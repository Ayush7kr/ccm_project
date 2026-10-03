from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import User
from .decorators import admin_required
from campaigns.models import Campaign
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, FollowUp

def home_view(request):
    """
    Public CCM Home / Landing Page.
    Accessible without authentication.
    """
    try:
        stats = {
            'total_campaigns': Campaign.objects.filter(status='Active').count(),
            'total_customers': Customer.objects.count(),
            'total_calls': CallRecord.objects.count(),
            'total_telecallers': User.objects.filter(role='TELE_CALLER', is_active=True).count(),
        }
    except Exception:
        stats = {
            'total_campaigns': 0,
            'total_customers': 0,
            'total_calls': 0,
            'total_telecallers': 0,
        }
    return render(request, 'public/home.html', {
        'stats': stats,
    })

def health_check(request):
    """
    Health check endpoint returning system & DB status.
    """
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Exception:
        db_ok = False

    status = "healthy" if db_ok else "unhealthy"
    status_code = 200 if db_ok else 503
    return JsonResponse({
        "status": status,
        "database": "connected" if db_ok else "disconnected",
    }, status=status_code)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    errors = {}
    form_data = {}
    raw_role = (request.GET.get('role', '') or request.POST.get('selected_role', '')).strip().upper()
    if raw_role in ['ADMIN', 'ADMINISTRATOR']:
        selected_role = 'ADMIN'
    elif raw_role in ['TELE_CALLER', 'TELECALLER', 'TELE-CALLER']:
        selected_role = 'TELE_CALLER'
    else:
        selected_role = raw_role

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        remember_me = request.POST.get('remember_me')
        post_role = (request.POST.get('selected_role') or '').strip().upper()
        if post_role in ['ADMIN', 'ADMINISTRATOR']:
            selected_role = 'ADMIN'
        elif post_role in ['TELE_CALLER', 'TELECALLER', 'TELE-CALLER']:
            selected_role = 'TELE_CALLER'
        elif post_role:
            selected_role = post_role

        form_data['username'] = username

        if not username:
            errors['username'] = 'Username or email is required.'
        if not password:
            errors['password'] = 'Password is required.'

        if not errors:
            user = authenticate(request, username=username, password=password)
            if user is None and '@' in username:
                # Try finding by email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                if not user.is_active:
                    errors['general'] = 'Your account has been deactivated. Please contact an administrator.'
                elif selected_role == 'ADMIN' and not user.is_admin_user:
                    errors['general'] = 'The selected role does not match this account. Please select the correct role.'
                elif selected_role == 'TELE_CALLER' and not user.is_telecaller_user:
                    errors['general'] = 'The selected role does not match this account. Please select the correct role.'
                else:
                    auth_login(request, user)
                    if not remember_me:
                        request.session.set_expiry(0)  # Expires when browser closes
                    messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                    return redirect('dashboard')
            else:
                user_check = User.objects.filter(username=username).first()
                if not user_check and '@' in username:
                    user_check = User.objects.filter(email=username).first()
                if user_check and user_check.check_password(password) and not user_check.is_active:
                    errors['general'] = 'Your account has been deactivated. Please contact an administrator.'
                else:
                    errors['general'] = 'Invalid username or password.'

    return render(request, 'auth/login.html', {
        'errors': errors,
        'form_data': form_data,
        'selected_role': selected_role,
    })

@login_required
def logout_view(request):
    if request.method == 'POST':
        auth_logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect('login')

def telecaller_register(request):
    """
    Public self-registration view for Tele-callers.
    Provisions TELE_CALLER account with secure PBKDF2 hashed storage,
    phone number, full name, in-app welcome notification, and administrator notification.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    errors = {}
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        terms_accepted = request.POST.get('terms_accepted')

        form_data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
        }

        # Validate Username
        if not username:
            errors['username'] = 'Username is required.'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters long.'
        elif not username.replace('_', '').isalnum():
            errors['username'] = 'Username may only contain letters, numbers, and underscores.'
        elif User.objects.filter(username__iexact=username).exists():
            errors['username'] = 'This username is already taken. Please choose another.'

        # Validate Name
        if not first_name:
            errors['first_name'] = 'First name is required.'

        # Validate Email
        if not email:
            errors['email'] = 'Email address is required.'
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors['email'] = 'Please enter a valid email address.'
        elif User.objects.filter(email__iexact=email).exists():
            errors['email'] = 'This email is already registered. Please sign in instead.'

        # Validate Phone
        if not phone:
            errors['phone'] = 'Phone number is required.'
        elif len(''.join(filter(str.isdigit, phone))) < 7:
            errors['phone'] = 'Please enter a valid phone number.'

        # Validate Password
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'

        if not terms_accepted:
            errors['terms'] = 'You must agree to the Tele-calling guidelines.'

        if not errors:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role='TELE_CALLER',
                is_active=True
            )

            # In-App Welcome Notification
            try:
                from analytics.models import Notification
                Notification.objects.create(
                    recipient=user,
                    notification_type='assignment',
                    title='Welcome to CCM!',
                    message=f'Hello {user.first_name or user.username}! Your tele-caller account is active. You can now access your workspace and start calling assigned leads.',
                    related_object_type='system'
                )

                admin_users = User.objects.filter(role='ADMIN', is_active=True)
                for admin in admin_users:
                    Notification.objects.create(
                        recipient=admin,
                        notification_type='system',
                        title='New Tele-caller Registered',
                        message=f'Tele-caller {user.get_full_name() or user.username} (@{user.username}) registered on the platform.',
                        related_object_type='telecaller',
                        related_object_id=user.id
                    )
            except Exception:
                pass

            auth_login(request, user)
            messages.success(request, f"Welcome to CCM, {user.get_full_name() or user.username}! Your tele-caller account is ready.")
            return redirect('dashboard')

    return render(request, 'auth/register.html', {
        'errors': errors,
        'form_data': form_data,
    })

from django.db.models import Count, Q, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce

@admin_required
def telecaller_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    telecallers = User.objects.filter(role='TELE_CALLER')

    if search_query:
        telecallers = telecallers.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    if status_filter == 'active':
        telecallers = telecallers.filter(is_active=True)
    elif status_filter == 'inactive':
        telecallers = telecallers.filter(is_active=False)

    assigned_sub = Subquery(
        CampaignCustomer.objects.filter(assigned_telecaller=OuterRef('pk'))
        .values('assigned_telecaller')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1],
        output_field=IntegerField()
    )
    pending_sub = Subquery(
        CampaignCustomer.objects.filter(
            assigned_telecaller=OuterRef('pk'),
            assignment_status__in=['Assigned', 'In Progress']
        )
        .values('assigned_telecaller')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1],
        output_field=IntegerField()
    )
    completed_sub = Subquery(
        CallRecord.objects.filter(
            telecaller=OuterRef('pk'),
            call_status='Completed'
        )
        .values('telecaller')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1],
        output_field=IntegerField()
    )
    followups_sub = Subquery(
        FollowUp.objects.filter(
            assigned_to=OuterRef('pk'),
            status='Pending'
        )
        .values('assigned_to')
        .annotate(cnt=Count('id'))
        .values('cnt')[:1],
        output_field=IntegerField()
    )

    telecallers = telecallers.annotate(
        annotated_assigned=Coalesce(assigned_sub, Value(0)),
        annotated_pending=Coalesce(pending_sub, Value(0)),
        annotated_completed=Coalesce(completed_sub, Value(0)),
        annotated_followups=Coalesce(followups_sub, Value(0)),
    )

    telecaller_data = []
    for tc in telecallers:
        assigned_count = tc.annotated_assigned
        completed_calls = tc.annotated_completed
        pending_calls = tc.annotated_pending
        followups_due = tc.annotated_followups
        completion_rate = round((completed_calls / assigned_count * 100), 1) if assigned_count > 0 else 0

        telecaller_data.append({
            'user': tc,
            'assigned_count': assigned_count,
            'completed_calls': completed_calls,
            'pending_calls': pending_calls,
            'followups_due': followups_due,
            'completion_rate': completion_rate,
        })

    return render(request, 'telecallers/list.html', {
        'telecallers': telecaller_data,
        'search_query': search_query,
        'status_filter': status_filter,
    })

@admin_required
def telecaller_create(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        form_data = {
            'username': username, 'email': email, 'first_name': first_name,
            'last_name': last_name, 'phone': phone
        }

        if not username:
            errors['username'] = 'Username is required.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Username is already taken.'

        if not password or len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters.'

        if email and User.objects.filter(email=email).exists():
            errors['email'] = 'Email is already registered.'

        if not errors:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role='TELE_CALLER'
            )

            try:
                from analytics.models import Notification
                Notification.objects.create(
                    recipient=user,
                    notification_type='assignment',
                    title='Welcome to CCM!',
                    message=f'Hello {user.first_name or user.username}! Your tele-caller account has been provisioned by an administrator. You can now access your campaigns and start calling assigned leads.',
                    related_object_type='system'
                )
            except Exception:
                pass

            messages.success(request, f"Tele-caller '{user.username}' created successfully!")
            return redirect('telecaller_list')

    return render(request, 'telecallers/form.html', {
        'errors': errors,
        'form_data': form_data,
        'is_edit': False
    })

@admin_required
def telecaller_detail(request, pk):
    telecaller = get_object_or_404(User, pk=pk, role='TELE_CALLER')
    
    assigned_customers_qs = CampaignCustomer.objects.filter(assigned_telecaller=telecaller).select_related('customer', 'campaign')
    all_calls_qs = CallRecord.objects.filter(telecaller=telecaller)
    followups_qs = FollowUp.objects.filter(assigned_to=telecaller).select_related('customer')

    assigned_count = assigned_customers_qs.count()
    completed_calls = all_calls_qs.filter(call_status='Completed').count()
    pending_count = assigned_customers_qs.filter(assignment_status__in=['Assigned', 'In Progress']).count()
    completion_rate = round((completed_calls / assigned_count * 100), 1) if assigned_count > 0 else 0

    assigned_campaigns = Campaign.objects.filter(customer_assignments__assigned_telecaller=telecaller).distinct()

    # Order and slice only when preparing context
    call_records = all_calls_qs.select_related('customer', 'campaign').order_by('-created_at')[:20]
    followups = followups_qs.order_by('-scheduled_date')[:10]
    assigned_customers = assigned_customers_qs[:15]

    return render(request, 'telecallers/detail.html', {
        'telecaller': telecaller,
        'assigned_campaigns': assigned_campaigns,
        'assigned_customers': assigned_customers,
        'call_records': call_records,
        'followups': followups,
        'assigned_count': assigned_count,
        'completed_calls': completed_calls,
        'pending_count': pending_count,
        'completion_rate': completion_rate
    })

@admin_required
def telecaller_edit(request, pk):
    """
    Admin edits tele-caller profile metadata.
    NOTE: Direct password editing has been removed for security.
    Use the separate telecaller_reset_password workflow to reset credentials.
    """
    telecaller = get_object_or_404(User, pk=pk, role='TELE_CALLER')
    errors = {}

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if email and User.objects.filter(email=email).exclude(pk=telecaller.pk).exists():
            errors['email'] = 'Email is already used by another user.'

        if not errors:
            telecaller.email = email
            telecaller.first_name = first_name
            telecaller.last_name = last_name
            telecaller.phone = phone
            telecaller.is_active = is_active
            telecaller.save()

            messages.success(request, f"Tele-caller '{telecaller.username}' updated successfully!")
            return redirect('telecaller_detail', pk=telecaller.pk)

    form_data = {
        'username': telecaller.username,
        'email': telecaller.email,
        'first_name': telecaller.first_name,
        'last_name': telecaller.last_name,
        'phone': telecaller.phone,
        'is_active': telecaller.is_active
    }

    return render(request, 'telecallers/form.html', {
        'telecaller': telecaller,
        'form_data': form_data,
        'errors': errors,
        'is_edit': True
    })

@admin_required
def telecaller_reset_password(request, pk):
    """
    Dedicated secure password reset initiation by Admin for a Tele-caller.
    Does NOT expose existing passwords or allow direct password overwrites in profile edit.
    """
    telecaller = get_object_or_404(User, pk=pk, role='TELE_CALLER')

    if not telecaller.is_active:
        messages.error(request, f"Cannot reset password for deactivated account '{telecaller.username}'. Please activate the account first.")
        return redirect('telecaller_detail', pk=telecaller.pk)

    if not telecaller.email:
        messages.error(request, f"Tele-caller '{telecaller.username}' does not have a registered email address. Please update their profile with an email first.")
        return redirect('telecaller_edit', pk=telecaller.pk)

    if request.method == 'POST':
        token = default_token_generator.make_token(telecaller)
        uidb64 = urlsafe_base64_encode(force_bytes(telecaller.pk))
        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
        )

        subject = "CCM Account Password Reset Request"
        message = (
            f"Hello {telecaller.get_full_name() or telecaller.username},\n\n"
            f"An administrator has initiated a password reset for your CCM Campaign Call Manager account.\n\n"
            f"Please click the link below to set your new password:\n"
            f"{reset_url}\n\n"
            f"If you did not expect this request, please contact your system administrator.\n\n"
            f"— CCM Team"
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [telecaller.email],
                fail_silently=False,
            )
            messages.success(
                request,
                f"Password reset link has been dispatched to {telecaller.email}."
            )
        except Exception as e:
            messages.warning(
                request,
                f"Password reset initiated. Reset link: {reset_url}"
            )

        return redirect('telecaller_detail', pk=telecaller.pk)

    return render(request, 'telecallers/reset_password_confirm.html', {
        'telecaller': telecaller,
    })

def user_password_reset_confirm(request, uidb64, token):
    """
    Secure password reset confirmation page where user sets their new password.
    Accessible via the emailed reset link.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    valid_link = bool(user is not None and default_token_generator.check_token(user, token))

    if user and not user.is_active:
        messages.error(request, "This account has been deactivated. Password reset is not permitted.")
        return redirect('login')

    errors = {}
    if request.method == 'POST' and valid_link:
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password or len(new_password) < 6:
            errors['new_password'] = "Password must be at least 6 characters."
        elif new_password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            user.set_password(new_password)
            user.save()
            messages.success(request, f"Password for {user.username} has been reset successfully! Please sign in with your new password.")
            return redirect('login')

    return render(request, 'auth/password_reset_confirm.html', {
        'valid_link': valid_link,
        'user_obj': user,
        'errors': errors,
    })

def custom_bad_request(request, exception=None):
    return render(request, 'errors/400.html', status=400)

def custom_permission_denied(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def custom_page_not_found(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def custom_server_error(request):
    return render(request, 'errors/500.html', status=500)
