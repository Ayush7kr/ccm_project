from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.db import transaction
from django.core.paginator import Paginator
from datetime import datetime

from .models import Campaign, Questionnaire, Question
from accounts.decorators import admin_required
from customers.models import CampaignCustomer, Customer
from calls.models import CallRecord, FollowUp

@login_required
def campaign_list(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    campaigns = Campaign.objects.all()

    # If Tele-caller, filter only campaigns with customers assigned to them
    if request.user.is_telecaller_user:
        assigned_campaign_ids = CampaignCustomer.objects.filter(
            assigned_telecaller=request.user
        ).values_list('campaign_id', flat=True).distinct()
        campaigns = campaigns.filter(id__in=assigned_campaign_ids)

    if search_query:
        campaigns = campaigns.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query) | Q(campaign_type__icontains=search_query)
        )

    if status_filter:
        campaigns = campaigns.filter(status=status_filter)

    campaign_data = []
    for camp in campaigns:
        total_customers = CampaignCustomer.objects.filter(campaign=camp).count()
        completed_calls = CallRecord.objects.filter(campaign=camp, call_status='Completed').count()
        progress_pct = round((completed_calls / camp.target_calls * 100), 1) if camp.target_calls > 0 else 0
        if progress_pct > 100:
            progress_pct = 100

        campaign_data.append({
            'campaign': camp,
            'total_customers': total_customers,
            'completed_calls': completed_calls,
            'progress_pct': progress_pct,
            'has_questionnaire': hasattr(camp, 'questionnaire')
        })

    paginator = Paginator(campaign_data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'campaigns/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    })

@admin_required
def campaign_create(request):
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        campaign_type = request.POST.get('campaign_type', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        status = request.POST.get('status', 'Draft').strip()
        target_calls = request.POST.get('target_calls', '0').strip()

        form_data = {
            'name': name, 'description': description, 'campaign_type': campaign_type,
            'start_date': start_date, 'end_date': end_date, 'status': status,
            'target_calls': target_calls
        }

        if not name:
            errors['name'] = 'Campaign name is required.'
        if not start_date:
            errors['start_date'] = 'Start date is required.'
        if not end_date:
            errors['end_date'] = 'End date is required.'

        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                if ed < sd:
                    errors['end_date'] = 'End date must be on or after start date.'
            except ValueError:
                errors['dates'] = 'Invalid date format.'

        try:
            target_calls_int = int(target_calls)
            if target_calls_int < 0:
                errors['target_calls'] = 'Target calls cannot be negative.'
        except ValueError:
            errors['target_calls'] = 'Target calls must be an integer.'

        if not errors:
            campaign = Campaign.objects.create(
                name=name,
                description=description,
                campaign_type=campaign_type or 'Tele-calling',
                start_date=start_date,
                end_date=end_date,
                status=status,
                target_calls=target_calls_int,
                created_by=request.user
            )
            messages.success(request, f"Campaign '{campaign.name}' created successfully!")
            return redirect('campaign_detail', pk=campaign.pk)

    return render(request, 'campaigns/form.html', {
        'errors': errors,
        'form_data': form_data,
        'is_edit': False
    })

@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)

    # Permission check for tele-callers
    if request.user.is_telecaller_user:
        is_assigned = CampaignCustomer.objects.filter(campaign=campaign, assigned_telecaller=request.user).exists()
        if not is_assigned:
            messages.error(request, "You are not assigned to this campaign.")
            return redirect('campaign_list')

    active_tab = request.GET.get('tab', 'overview')
    if request.user.is_telecaller_user and active_tab == 'analytics':
        active_tab = 'overview'

    # Data aggregates
    assignments = CampaignCustomer.objects.filter(campaign=campaign).select_related('customer', 'assigned_telecaller')
    if request.user.is_telecaller_user:
        assignments = assignments.filter(assigned_telecaller=request.user)

    total_customers = assignments.count()
    assigned_count = assignments.exclude(assigned_telecaller__isnull=True).count()
    call_records = CallRecord.objects.filter(campaign=campaign).select_related('customer', 'telecaller')
    if request.user.is_telecaller_user:
        call_records = call_records.filter(telecaller=request.user)

    completed_calls = call_records.filter(call_status='Completed').count()
    pending_calls = assignments.filter(assignment_status__in=['Assigned', 'In Progress', 'Unassigned']).count()
    followups_count = FollowUp.objects.filter(customer__campaign_links__campaign=campaign).distinct().count()

    progress_pct = round((completed_calls / campaign.target_calls * 100), 1) if campaign.target_calls > 0 else 0
    if progress_pct > 100: progress_pct = 100

    questionnaire = getattr(campaign, 'questionnaire', None)
    questions = questionnaire.questions.all() if questionnaire else []

    # Campaign Specific Analytics
    from django.db.models import Avg
    all_campaign_calls = CallRecord.objects.filter(campaign=campaign)
    status_counts = {
        'Completed': all_campaign_calls.filter(call_status='Completed').count(),
        'No_Answer': all_campaign_calls.filter(call_status='No Answer').count(),
        'Unreachable': all_campaign_calls.filter(call_status='Unreachable').count(),
        'Busy': all_campaign_calls.filter(call_status='Busy').count(),
        'Follow_up_Required': all_campaign_calls.filter(call_status='Follow-up Required').count(),
    }

    avg_call_duration = round(all_campaign_calls.filter(call_status='Completed').aggregate(avg=Avg('duration'))['avg'] or 0, 1)

    question_analytics = []
    if questionnaire:
        from calls.models import QuestionResponse
        for q in questions:
            resps = QuestionResponse.objects.filter(question=q, call_record__campaign=campaign)
            total_r = resps.count()
            q_info = {
                'question': q,
                'total_responses': total_r,
                'counts': {},
                'avg_rating': None,
                'text_responses': []
            }
            if q.question_type in ['single_choice', 'yes_no', 'multiple_choice']:
                counts = {}
                for r in resps:
                    for opt in r.selected_options:
                        counts[opt] = counts.get(opt, 0) + 1
                q_info['counts'] = counts
            elif q.question_type == 'rating_scale':
                avg_r = resps.aggregate(avg=Avg('rating'))['avg'] or 0
                q_info['avg_rating'] = round(avg_r, 2)
                q_info['counts'] = {str(i): resps.filter(rating=i).count() for i in range(1, 6)}
            elif q.question_type == 'open_ended':
                q_info['text_responses'] = list(resps.exclude(response_text='').values_list('response_text', flat=True)[:5])

            question_analytics.append(q_info)

    return render(request, 'campaigns/detail.html', {
        'campaign': campaign,
        'active_tab': active_tab,
        'assignments': assignments[:50],
        'call_records': call_records[:50],
        'total_customers': total_customers,
        'assigned_count': assigned_count,
        'completed_calls': completed_calls,
        'pending_calls': pending_calls,
        'followups_count': followups_count,
        'progress_pct': progress_pct,
        'questionnaire': questionnaire,
        'questions': questions,
        'status_counts': status_counts,
        'avg_call_duration': avg_call_duration,
        'question_analytics': question_analytics,
    })


@admin_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        campaign_type = request.POST.get('campaign_type', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        status = request.POST.get('status', 'Draft').strip()
        target_calls = request.POST.get('target_calls', '0').strip()

        if not name: errors['name'] = 'Campaign name is required.'
        if not start_date: errors['start_date'] = 'Start date is required.'
        if not end_date: errors['end_date'] = 'End date is required.'

        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                if ed < sd: errors['end_date'] = 'End date must be on or after start date.'
            except ValueError:
                errors['dates'] = 'Invalid date format.'

        try:
            target_calls_int = int(target_calls)
        except ValueError:
            target_calls_int = 0

        if not errors:
            campaign.name = name
            campaign.description = description
            campaign.campaign_type = campaign_type or 'Tele-calling'
            campaign.start_date = start_date
            campaign.end_date = end_date
            campaign.status = status
            campaign.target_calls = target_calls_int
            campaign.save()

            messages.success(request, f"Campaign '{campaign.name}' updated successfully!")
            return redirect('campaign_detail', pk=campaign.pk)

    form_data = {
        'name': campaign.name,
        'description': campaign.description,
        'campaign_type': campaign.campaign_type,
        'start_date': campaign.start_date.strftime('%Y-%m-%d') if campaign.start_date else '',
        'end_date': campaign.end_date.strftime('%Y-%m-%d') if campaign.end_date else '',
        'status': campaign.status,
        'target_calls': campaign.target_calls
    }

    return render(request, 'campaigns/form.html', {
        'campaign': campaign,
        'form_data': form_data,
        'errors': errors,
        'is_edit': True
    })

@admin_required
def campaign_status_toggle(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_transitions = {
            'Draft': ['Active'],
            'Active': ['Paused', 'Completed'],
            'Paused': ['Active', 'Completed'],
            'Completed': ['Active'],
        }

        allowed = valid_transitions.get(campaign.status, [])
        if new_status not in allowed:
            messages.error(request, f"Invalid transition: Cannot change status from '{campaign.status}' directly to '{new_status}'. Allowed transitions: {', '.join(allowed) or 'None'}.")
            return redirect('campaign_detail', pk=campaign.pk)

        # Date awareness
        from django.utils import timezone
        today = timezone.localtime().date()
        if new_status == 'Active' and campaign.end_date and campaign.end_date < today:
            messages.warning(request, f"Notice: Campaign end date ({campaign.end_date}) is in the past. Status set to Active.")

        campaign.status = new_status
        campaign.save()
        messages.success(request, f"Campaign status transitioned to '{new_status}'.")
    return redirect('campaign_detail', pk=campaign.pk)


@admin_required
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        name = campaign.name
        campaign.delete()
        messages.success(request, f"Campaign '{name}' has been deleted.")
        return redirect('campaign_list')
    return render(request, 'campaigns/confirm_delete.html', {'campaign': campaign})

# --- QUESTIONNAIRE BUILDER VIEWS ---

@admin_required
def questionnaire_builder(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    questionnaire, created = Questionnaire.objects.get_or_create(
        campaign=campaign,
        defaults={
            'title': f"Questionnaire for {campaign.name}",
            'created_by': request.user
        }
    )

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()

        questionnaire.title = title or f"Questionnaire for {campaign.name}"
        questionnaire.description = description

        # Parse questions
        question_ids = request.POST.getlist('q_id[]')
        texts = request.POST.getlist('q_text[]')
        types = request.POST.getlist('q_type[]')
        options_raw = request.POST.getlist('q_options[]')
        requireds = request.POST.getlist('q_required[]')

        validation_errors = []
        parsed_questions = []

        for i in range(len(texts)):
            q_text = texts[i].strip()
            if not q_text:
                continue

            q_type = types[i] if i < len(types) else 'open_ended'
            opts_str = options_raw[i] if i < len(options_raw) else ''
            opts_list = [o.strip() for o in opts_str.split(',') if o.strip()]
            is_req = (requireds[i] == '1') if i < len(requireds) else True
            q_id = question_ids[i] if i < len(question_ids) and question_ids[i] else None

            # Validate options based on question_type
            if q_type in ['single_choice', 'multiple_choice']:
                if len(opts_list) < 2:
                    validation_errors.append(f"Question '{q_text}' ({'Single Choice' if q_type=='single_choice' else 'Multiple Choice'}) requires at least 2 non-empty options.")
            elif q_type == 'yes_no':
                opts_list = ['Yes', 'No']
            elif q_type == 'rating_scale':
                opts_list = ['1', '2', '3', '4', '5']
            elif q_type == 'open_ended':
                opts_list = []

            parsed_questions.append({
                'q_id': q_id,
                'question_text': q_text,
                'question_type': q_type,
                'options': opts_list,
                'required': is_req,
                'order': i + 1
            })

        if validation_errors:
            for err in validation_errors:
                messages.error(request, err)
            return render(request, 'questionnaires/builder.html', {
                'campaign': campaign,
                'questionnaire': questionnaire,
                'questions': questionnaire.questions.all()
            })

        with transaction.atomic():
            questionnaire.save()
            existing_ids = set()
            for q_data in parsed_questions:
                if q_data['q_id']:
                    try:
                        q_obj = Question.objects.get(pk=q_data['q_id'], questionnaire=questionnaire)
                        q_obj.question_text = q_data['question_text']
                        q_obj.question_type = q_data['question_type']
                        q_obj.options = q_data['options']
                        q_obj.required = q_data['required']
                        q_obj.order = q_data['order']
                        q_obj.save()
                        existing_ids.add(q_obj.id)
                    except Question.DoesNotExist:
                        pass
                else:
                    new_q = Question.objects.create(
                        questionnaire=questionnaire,
                        question_text=q_data['question_text'],
                        question_type=q_data['question_type'],
                        options=q_data['options'],
                        required=q_data['required'],
                        order=q_data['order']
                    )
                    existing_ids.add(new_q.id)

            # Delete questions removed from form
            Question.objects.filter(questionnaire=questionnaire).exclude(id__in=existing_ids).delete()

        messages.success(request, "Questionnaire saved successfully!")
        return redirect('campaign_detail', pk=campaign.id)

    questions = questionnaire.questions.all()

    return render(request, 'questionnaires/builder.html', {
        'campaign': campaign,
        'questionnaire': questionnaire,
        'questions': questions
    })

@login_required
def questionnaire_preview(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    questionnaire = getattr(campaign, 'questionnaire', None)
    questions = questionnaire.questions.all() if questionnaire else []

    return render(request, 'questionnaires/preview.html', {
        'campaign': campaign,
        'questionnaire': questionnaire,
        'questions': questions
    })

