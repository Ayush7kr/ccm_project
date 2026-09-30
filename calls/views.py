from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from .models import CallRecord, QuestionResponse, FollowUp
from customers.models import CampaignCustomer, Customer
from campaigns.models import Campaign, Question
from analytics.models import Notification

def update_overdue_followups(user=None):
    """Utility to mark pending follow-ups as overdue based on date AND time in local timezone."""
    now = timezone.localtime()
    qs = FollowUp.objects.filter(status='Pending')
    if user and user.is_telecaller_user:
        qs = qs.filter(assigned_to=user)

    for fu in qs:
        if fu.scheduled_date and fu.scheduled_time:
            scheduled_dt = timezone.make_aware(
                datetime.combine(fu.scheduled_date, fu.scheduled_time),
                timezone.get_current_timezone()
            )
            if scheduled_dt < now:
                fu.status = 'Overdue'
                fu.save()
                # Create notification if not already created
                Notification.objects.get_or_create(
                    recipient=fu.assigned_to,
                    notification_type='followup',
                    title='Follow-up Overdue',
                    message=f"Follow-up with {fu.customer.name} scheduled for {fu.scheduled_date} at {fu.scheduled_time} is now overdue.",
                    related_object_type='followup',
                    related_object_id=fu.id
                )

from django.db.models import Q
from accounts.models import User

@login_required
def call_list(request):
    """View call logs history with comprehensive multi-criteria filtering"""
    calls = CallRecord.objects.all().select_related('customer', 'campaign', 'telecaller')

    if request.user.is_telecaller_user:
        calls = calls.filter(telecaller=request.user)

    search_query = request.GET.get('q', '').strip()
    campaign_id = request.GET.get('campaign', '').strip()
    telecaller_id = request.GET.get('telecaller', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        calls = calls.filter(
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query) |
            Q(customer__company__icontains=search_query) |
            Q(comments__icontains=search_query)
        )

    if campaign_id:
        calls = calls.filter(campaign_id=campaign_id)

    if telecaller_id and request.user.is_admin_user:
        calls = calls.filter(telecaller_id=telecaller_id)

    if status_filter:
        calls = calls.filter(call_status=status_filter)

    campaigns = Campaign.objects.all()
    telecallers = User.objects.filter(role='TELE_CALLER') if request.user.is_admin_user else []

    return render(request, 'calls/call_list.html', {
        'calls': calls[:100],
        'search_query': search_query,
        'campaign_id': campaign_id,
        'telecaller_id': telecaller_id,
        'status_filter': status_filter,
        'campaigns': campaigns,
        'telecallers': telecallers,
    })


@login_required
def record_call(request, assignment_id):
    """Tele-caller Call Console Workflow with Strict RBAC & Questionnaire Validation"""
    assignment = get_object_or_404(CampaignCustomer, pk=assignment_id)
    campaign = assignment.campaign
    customer = assignment.customer

    # Strict Access Control:
    if request.user.is_telecaller_user:
        if assignment.assigned_telecaller != request.user:
            messages.error(request, "Access denied: This customer is not assigned to you.")
            return redirect('customer_list')
        if campaign.status != 'Active':
            messages.error(request, "Access denied: Calls can only be recorded for Active campaigns.")
            return redirect('campaign_detail', pk=campaign.pk)
        if assignment.assignment_status == 'Completed':
            messages.error(request, "Access denied: This customer assignment has already been completed.")
            return redirect('campaign_detail', pk=campaign.pk)

    questionnaire = getattr(campaign, 'questionnaire', None)
    questions = questionnaire.questions.all() if questionnaire else []
    previous_calls = CallRecord.objects.filter(customer=customer, campaign=campaign).order_by('-created_at')

    if request.method == 'POST':
        call_status = request.POST.get('call_status', '').strip()
        duration = request.POST.get('duration', '0').strip()
        comments = request.POST.get('comments', '').strip()

        # Followup fields
        schedule_followup = request.POST.get('schedule_followup') == 'on' or call_status == 'Follow-up Required'
        fu_date = request.POST.get('followup_date', '').strip()
        fu_time = request.POST.get('followup_time', '').strip()
        fu_notes = request.POST.get('followup_notes', '').strip()

        try:
            duration_sec = max(0, int(duration))
        except ValueError:
            duration_sec = 0

        errors = []

        if not call_status:
            errors.append("Please select a call outcome status.")

        # Require follow-up details if call status is Follow-up Required
        if call_status == 'Follow-up Required' and (not fu_date or not fu_time):
            errors.append("Please specify both date and time for the required follow-up.")

        # Questionnaire Validation if Call is Completed
        responses_to_create = []
        if call_status == 'Completed' and questions:
            for q in questions:
                field_name = f"question_{q.id}"
                if q.question_type == 'multiple_choice':
                    selected_opts = [o.strip() for o in request.POST.getlist(field_name) if o.strip()]
                    if q.required and not selected_opts:
                        errors.append(f"Question '{q.question_text}' is required.")
                    elif selected_opts:
                        responses_to_create.append({
                            'question': q,
                            'selected_options': [o for o in selected_opts if o in q.options]
                        })
                elif q.question_type == 'rating_scale':
                    rating_val = request.POST.get(field_name, '').strip()
                    if q.required and not rating_val:
                        errors.append(f"Question '{q.question_text}' is required.")
                    elif rating_val:
                        try:
                            r_int = int(rating_val)
                            if 1 <= r_int <= 5:
                                responses_to_create.append({'question': q, 'rating': r_int})
                            else:
                                errors.append(f"Rating for '{q.question_text}' must be between 1 and 5.")
                        except ValueError:
                            errors.append(f"Invalid rating value for '{q.question_text}'.")
                elif q.question_type in ['single_choice', 'yes_no']:
                    opt_val = request.POST.get(field_name, '').strip()
                    valid_opts = q.options if q.options else (['Yes', 'No'] if q.question_type == 'yes_no' else [])
                    if q.required and not opt_val:
                        errors.append(f"Question '{q.question_text}' is required.")
                    elif opt_val:
                        responses_to_create.append({'question': q, 'selected_options': [opt_val]})
                else:  # open_ended
                    text_val = request.POST.get(field_name, '').strip()
                    if q.required and not text_val:
                        errors.append(f"Question '{q.question_text}' is required.")
                    elif text_val:
                        responses_to_create.append({'question': q, 'response_text': text_val})

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'calls/record_call.html', {
                'assignment': assignment,
                'campaign': campaign,
                'customer': customer,
                'questionnaire': questionnaire,
                'questions': questions,
                'previous_calls': previous_calls
            })

        with transaction.atomic():
            start_time = timezone.now() - timezone.timedelta(seconds=duration_sec)
            end_time = timezone.now()

            call_record = CallRecord.objects.create(
                campaign=campaign,
                customer=customer,
                telecaller=request.user,
                call_status=call_status,
                call_start_time=start_time,
                call_end_time=end_time,
                duration=duration_sec,
                comments=comments
            )

            # Update CampaignCustomer assignment status
            if call_status == 'Completed':
                assignment.assignment_status = 'Completed'
            else:
                assignment.assignment_status = 'In Progress'
            assignment.save()

            # Save Question Responses
            if call_status == 'Completed':
                for resp_data in responses_to_create:
                    QuestionResponse.objects.create(
                        call_record=call_record,
                        **resp_data
                    )

            # Create Follow-up if scheduled or required
            if schedule_followup and fu_date and fu_time:
                FollowUp.objects.create(
                    call_record=call_record,
                    customer=customer,
                    assigned_to=request.user,
                    scheduled_date=fu_date,
                    scheduled_time=fu_time,
                    status='Pending',
                    notes=fu_notes or f"Follow-up scheduled from call status: {call_status}"
                )
                Notification.objects.create(
                    recipient=request.user,
                    notification_type='followup',
                    title='Follow-up Scheduled',
                    message=f"Follow-up set for {customer.name} on {fu_date} at {fu_time}.",
                    related_object_type='customer',
                    related_object_id=customer.id
                )

        messages.success(request, f"Call recorded successfully for {customer.name}.")
        return redirect('call_success', call_id=call_record.id)

    return render(request, 'calls/record_call.html', {
        'assignment': assignment,
        'campaign': campaign,
        'customer': customer,
        'questionnaire': questionnaire,
        'questions': questions,
        'previous_calls': previous_calls
    })

@login_required
def call_success(request, call_id):
    """Post-Call Confirmation view with View Customer and Next Customer actions"""
    call_record = get_object_or_404(CallRecord, pk=call_id)
    if request.user.is_telecaller_user and call_record.telecaller != request.user:
        messages.error(request, "Permission denied.")
        return redirect('dashboard')

    next_assignment = CampaignCustomer.objects.filter(
        campaign=call_record.campaign,
        assigned_telecaller=request.user,
        assignment_status__in=['Assigned', 'In Progress']
    ).exclude(customer=call_record.customer).first()

    followup = FollowUp.objects.filter(call_record=call_record).first()

    return render(request, 'calls/call_success.html', {
        'call_record': call_record,
        'next_assignment': next_assignment,
        'followup': followup
    })

# --- FOLLOW-UP MANAGEMENT VIEWS ---

@login_required
def followup_list(request):
    """List pending, overdue, and completed follow-ups"""
    update_overdue_followups(request.user)

    followups = FollowUp.objects.all().select_related('customer', 'assigned_to', 'call_record__campaign')
    if request.user.is_telecaller_user:
        followups = followups.filter(assigned_to=request.user)

    status_filter = request.GET.get('status', '')
    if status_filter:
        followups = followups.filter(status=status_filter)

    today = timezone.localtime().date()
    return render(request, 'followups/list.html', {
        'followups': followups,
        'status_filter': status_filter,
        'today': today
    })

@login_required
def followup_complete(request, pk):
    """Mark a follow-up as completed"""
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.is_telecaller_user and followup.assigned_to != request.user:
        messages.error(request, "Permission denied.")
        return redirect('followup_list')

    if request.method == 'POST':
        followup.status = 'Completed'
        followup.save()
        messages.success(request, f"Follow-up with {followup.customer.name} marked as completed!")

    return redirect('followup_list')

@login_required
def followup_cancel(request, pk):
    """Cancel a scheduled follow-up"""
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.is_telecaller_user and followup.assigned_to != request.user:
        messages.error(request, "Permission denied.")
        return redirect('followup_list')

    if request.method == 'POST':
        followup.status = 'Cancelled'
        followup.save()
        messages.success(request, f"Follow-up for {followup.customer.name} has been cancelled.")

    return redirect('followup_list')

