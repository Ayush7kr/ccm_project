import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Customer, CampaignCustomer
from campaigns.models import Campaign
from accounts.models import User
from accounts.decorators import admin_required
from calls.models import CallRecord, FollowUp

@login_required
def customer_list(request):
    search_query = request.GET.get('q', '').strip()
    campaign_filter = request.GET.get('campaign', '')
    status_filter = request.GET.get('status', '')

    customers = Customer.objects.all()

    # If tele-caller, restrict to assigned campaign customers or assigned follow-ups
    if request.user.is_telecaller_user:
        assigned_customer_ids = CampaignCustomer.objects.filter(
            assigned_telecaller=request.user
        ).values_list('customer_id', flat=True)
        followup_cust_ids = FollowUp.objects.filter(
            assigned_to=request.user
        ).values_list('customer_id', flat=True)
        customers = customers.filter(
            Q(id__in=assigned_customer_ids) | Q(id__in=followup_cust_ids)
        )

    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    if campaign_filter:
        customers = customers.filter(campaign_links__campaign_id=campaign_filter)

    if status_filter:
        customers = customers.filter(campaign_links__assignment_status=status_filter)

    customers = customers.distinct()

    paginator = Paginator(customers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Attach assignment info for listing display with efficient batch queries
    customer_list_data = []
    page_customers = list(page_obj)

    if page_customers:
        from collections import defaultdict

        # Batch fetch campaign links for the current page
        links_qs = CampaignCustomer.objects.filter(
            customer__in=page_customers
        ).select_related('campaign', 'assigned_telecaller')
        links_by_cust = defaultdict(list)
        for link in links_qs:
            links_by_cust[link.customer_id].append(link)

        # Batch fetch latest calls for the current page
        calls_qs = CallRecord.objects.filter(
            customer__in=page_customers
        ).order_by('-created_at')
        last_calls = {}
        for c in calls_qs:
            if c.customer_id not in last_calls:
                last_calls[c.customer_id] = c

        # Batch fetch pending followups for the current page
        fu_qs = FollowUp.objects.filter(
            customer__in=page_customers, status='Pending'
        ).order_by('scheduled_date', 'scheduled_time')
        pending_fus = {}
        for fu in fu_qs:
            if fu.customer_id not in pending_fus:
                pending_fus[fu.customer_id] = fu

        for cust in page_customers:
            customer_list_data.append({
                'customer': cust,
                'campaign_links': links_by_cust.get(cust.id, []),
                'last_call': last_calls.get(cust.id, None),
                'pending_followup': pending_fus.get(cust.id, None)
            })

    campaigns = Campaign.objects.all()

    return render(request, 'customers/list.html', {
        'customers_data': customer_list_data,
        'page_obj': page_obj,
        'search_query': search_query,
        'campaign_filter': campaign_filter,
        'status_filter': status_filter,
        'campaigns': campaigns,
    })

@admin_required
def customer_create(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        company = request.POST.get('company', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()

        form_data = {
            'name': name, 'phone': phone, 'email': email,
            'company': company, 'address': address, 'city': city, 'state': state
        }

        if not name:
            errors['name'] = 'Customer name is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'
        elif Customer.objects.filter(phone=phone).exists():
            errors['phone'] = 'A customer with this phone number already exists.'

        if not errors:
            customer = Customer.objects.create(
                name=name, phone=phone, email=email,
                company=company, address=address, city=city, state=state,
                source='Manual Input'
            )
            messages.success(request, f"Customer '{customer.name}' added successfully!")
            return redirect('customer_detail', pk=customer.pk)

    return render(request, 'customers/form.html', {
        'errors': errors,
        'form_data': form_data,
        'is_edit': False
    })

@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.user.is_telecaller_user:
        is_assigned = CampaignCustomer.objects.filter(customer=customer, assigned_telecaller=request.user).exists()
        has_followup = FollowUp.objects.filter(customer=customer, assigned_to=request.user).exists()
        if not is_assigned and not has_followup:
            messages.error(request, "You do not have access to this customer.")
            return redirect('customer_list')

    campaign_links = CampaignCustomer.objects.filter(customer=customer).select_related('campaign', 'assigned_telecaller')
    call_records = CallRecord.objects.filter(customer=customer).select_related('campaign', 'telecaller').prefetch_related('responses').order_by('-created_at')
    followups = FollowUp.objects.filter(customer=customer).select_related('assigned_to').order_by('scheduled_date')

    active_assignment = None
    if request.user.is_telecaller_user:
        active_assignment = CampaignCustomer.objects.filter(
            customer=customer,
            assigned_telecaller=request.user,
            campaign__status='Active'
        ).exclude(assignment_status='Completed').first()
    elif request.user.is_admin_user:
        active_assignment = CampaignCustomer.objects.filter(
            customer=customer,
            campaign__status='Active'
        ).exclude(assignment_status='Completed').first()

    return render(request, 'customers/detail.html', {
        'customer': customer,
        'campaign_links': campaign_links,
        'call_records': call_records,
        'followups': followups,
        'active_assignment': active_assignment,
    })


@admin_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        company = request.POST.get('company', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()

        if not name: errors['name'] = 'Customer name is required.'
        if not phone: errors['phone'] = 'Phone number is required.'
        elif Customer.objects.filter(phone=phone).exclude(pk=customer.pk).exists():
            errors['phone'] = 'Another customer already uses this phone number.'

        if not errors:
            customer.name = name
            customer.phone = phone
            customer.email = email
            customer.company = company
            customer.address = address
            customer.city = city
            customer.state = state
            customer.save()

            messages.success(request, f"Customer '{customer.name}' updated successfully!")
            return redirect('customer_detail', pk=customer.pk)

    form_data = {
        'name': customer.name, 'phone': customer.phone, 'email': customer.email,
        'company': customer.company, 'address': customer.address,
        'city': customer.city, 'state': customer.state
    }

    return render(request, 'customers/form.html', {
        'customer': customer,
        'form_data': form_data,
        'errors': errors,
        'is_edit': True
    })

@admin_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = customer.name
        customer.delete()
        messages.success(request, f"Customer '{name}' deleted.")
        return redirect('customer_list')
    return render(request, 'customers/confirm_delete.html', {'customer': customer})

# --- CSV / EXCEL IMPORT WORKFLOW ---

@admin_required
def customer_import_sample(request):
    """Download Sample CSV Template"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ccm_customer_import_sample.csv"'
    writer = csv.writer(response)
    writer.writerow(['name', 'phone', 'email', 'company', 'address', 'city', 'state'])
    writer.writerow(['Acme Corp Lead', '+15550199', 'lead@acme.com', 'Acme Corp', '123 Tech Blvd', 'San Francisco', 'CA'])
    writer.writerow(['Jane Smith', '+15550244', 'jane@smithco.org', 'Smith & Co', '456 Market St', 'Chicago', 'IL'])
    return response

@admin_required
def customer_import(request):
    """CSV / Excel Upload, Preview, Validation, and Confirmation"""
    if request.method == 'POST' and 'confirm_import' in request.POST:
        # Step 2: Confirmation & Execution
        import_rows = request.session.get('import_rows', [])
        target_campaign_id = request.POST.get('campaign_id')
        target_campaign = Campaign.objects.filter(pk=target_campaign_id).first() if target_campaign_id else None

        imported_count = 0
        skipped_count = 0
        errors_count = 0

        with transaction.atomic():
            for row in import_rows:
                if not row.get('is_valid'):
                    errors_count += 1
                    continue

                phone = row['phone']
                cust, created = Customer.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'name': row['name'],
                        'email': row['email'],
                        'company': row['company'],
                        'address': row['address'],
                        'city': row['city'],
                        'state': row['state'],
                        'source': 'CSV Import'
                    }
                )
                if created:
                    imported_count += 1
                else:
                    skipped_count += 1

                # If campaign selected, enroll in campaign
                if target_campaign:
                    CampaignCustomer.objects.get_or_create(
                        campaign=target_campaign,
                        customer=cust,
                        defaults={'assignment_status': 'Unassigned'}
                    )

        # Clear session
        if 'import_rows' in request.session:
            del request.session['import_rows']

        messages.success(
            request,
            f"Import complete! Successfully imported: {imported_count} new customers. Skipped duplicates: {skipped_count}. Errors: {errors_count}."
        )
        return redirect('customer_list')

    elif request.method == 'POST' and 'upload_file' in request.FILES:
        # Step 1: File Upload & Parsing
        uploaded_file = request.FILES['upload_file']
        filename = uploaded_file.name.lower()

        rows_parsed = []
        seen_phones = set()
        existing_phones = set(Customer.objects.values_list('phone', flat=True))

        if uploaded_file.size > 10 * 1024 * 1024:
            messages.error(request, "File size exceeds maximum allowed limit of 10 MB.")
            return redirect('customer_import')

        try:
            if filename.endswith('.csv'):
                file_bytes = uploaded_file.read()
                try:
                    decoded_file = file_bytes.decode('utf-8-sig')
                except UnicodeDecodeError:
                    decoded_file = file_bytes.decode('latin-1')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                for index, row in enumerate(reader, start=2):
                    name = str(row.get('name') or '').strip()
                    phone = str(row.get('phone') or '').strip()
                    email = str(row.get('email') or '').strip()
                    company = str(row.get('company') or '').strip()
                    address = str(row.get('address') or '').strip()
                    city = str(row.get('city') or '').strip()
                    state = str(row.get('state') or '').strip()

                    row_error = None
                    if not name:
                        row_error = 'Missing customer name'
                    elif not phone:
                        row_error = 'Missing phone number'
                    elif email and '@' not in email:
                        row_error = 'Invalid email address format'
                    elif phone in seen_phones:
                        row_error = 'Duplicate phone number in file'
                    elif phone in existing_phones:
                        row_error = 'Phone number already registered'

                    if phone:
                        seen_phones.add(phone)

                    rows_parsed.append({
                        'row_num': index,
                        'name': name,
                        'phone': phone,
                        'email': email,
                        'company': company,
                        'address': address,
                        'city': city,
                        'state': state,
                        'is_valid': row_error is None,
                        'error': row_error
                    })
            elif filename.endswith('.xls'):
                messages.error(request, "Legacy Excel (.xls) format is not supported. Please save your spreadsheet as .xlsx or .csv and upload again.")
                return redirect('customer_import')
            elif filename.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                sheet = wb.active
                headers = [str(cell.value).strip().lower() for cell in sheet[1] if cell.value]

                for index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row): continue
                    row_dict = dict(zip(headers, row))
                    name = str(row_dict.get('name') or '').strip()

                    raw_phone = row_dict.get('phone')
                    if isinstance(raw_phone, float) and raw_phone.is_integer():
                        phone = str(int(raw_phone))
                    elif raw_phone is not None:
                        phone = str(raw_phone).strip()
                        if phone.endswith('.0') and phone[:-2].replace('+', '').isdigit():
                            phone = phone[:-2]
                    else:
                        phone = ''

                    email = str(row_dict.get('email') or '').strip()
                    company = str(row_dict.get('company') or '').strip()
                    address = str(row_dict.get('address') or '').strip()
                    city = str(row_dict.get('city') or '').strip()
                    state = str(row_dict.get('state') or '').strip()

                    row_error = None
                    if not name: row_error = 'Missing customer name'
                    elif not phone: row_error = 'Missing phone number'
                    elif email and '@' not in email: row_error = 'Invalid email address format'
                    elif phone in seen_phones: row_error = 'Duplicate phone number in file'
                    elif phone in existing_phones: row_error = 'Phone number already registered'

                    if phone: seen_phones.add(phone)

                    rows_parsed.append({
                        'row_num': index,
                        'name': name,
                        'phone': phone,
                        'email': email,
                        'company': company,
                        'address': address,
                        'city': city,
                        'state': state,
                        'is_valid': row_error is None,
                        'error': row_error
                    })
            else:
                messages.error(request, "Unsupported file format. Please upload a .csv or .xlsx file.")
                return redirect('customer_import')
        except Exception as e:
            messages.error(request, f"Error parsing file: {str(e)}")
            return redirect('customer_import')

        # Save parsed preview into session
        request.session['import_rows'] = rows_parsed
        valid_rows_count = sum(1 for r in rows_parsed if r['is_valid'])
        invalid_rows_count = len(rows_parsed) - valid_rows_count

        campaigns = Campaign.objects.filter(status__in=['Draft', 'Active'])

        return render(request, 'customers/import_preview.html', {
            'rows': rows_parsed,
            'valid_count': valid_rows_count,
            'invalid_count': invalid_rows_count,
            'total_count': len(rows_parsed),
            'campaigns': campaigns
        })

    return render(request, 'customers/import.html')

# --- BULK CUSTOMER ASSIGNMENT ---

@admin_required
def customer_assign(request):
    if request.method == 'POST':
        campaign_id = request.POST.get('campaign_id')
        telecaller_id = request.POST.get('telecaller_id')
        customer_ids = request.POST.getlist('customer_ids')

        campaign = get_object_or_404(Campaign, pk=campaign_id)
        telecaller = get_object_or_404(User, pk=telecaller_id, role='TELE_CALLER')

        if campaign.status not in ['Draft', 'Active']:
            messages.error(request, f"Cannot assign customers to campaign '{campaign.name}' with status '{campaign.status}'. Only Draft or Active campaigns accept assignments.")
            return redirect('customer_assign')

        if not telecaller.is_active:
            messages.error(request, f"Cannot assign customers to inactive tele-caller '{telecaller.username}'.")
            return redirect('customer_assign')

        if not customer_ids:
            messages.error(request, "Please select at least one customer to assign.")
            return redirect('customer_assign')

        assigned_count = 0
        with transaction.atomic():
            for cust_id in customer_ids:
                customer = Customer.objects.filter(pk=cust_id).first()
                if not customer:
                    continue
                link, created = CampaignCustomer.objects.get_or_create(
                    campaign=campaign,
                    customer=customer
                )
                link.assigned_telecaller = telecaller
                link.assignment_status = 'Assigned' if link.assignment_status == 'Unassigned' else link.assignment_status
                link.assigned_at = timezone.now()
                link.save()
                assigned_count += 1

        # Create notification for tele-caller
        from analytics.models import Notification
        Notification.objects.create(
            recipient=telecaller,
            notification_type='assignment',
            title='New Customer Assignments',
            message=f"You have been assigned {assigned_count} customers in campaign '{campaign.name}'.",
            related_object_type='campaign',
            related_object_id=campaign.id
        )

        messages.success(request, f"Successfully assigned {assigned_count} customers to {telecaller.get_full_name() or telecaller.username}!")
        return redirect('campaign_detail', pk=campaign.id)

    campaigns = Campaign.objects.filter(status__in=['Draft', 'Active'])
    telecallers = User.objects.filter(role='TELE_CALLER', is_active=True)
    customers = Customer.objects.all()[:100]

    return render(request, 'customers/assign.html', {
        'campaigns': campaigns,
        'telecallers': telecallers,
        'customers': customers
    })
