"""
CCM Analytics Engine — Reusable query functions for consistent metrics
across dashboards, analytics, and reports.

All KPI calculations are centralized here to prevent data inconsistency.
"""
from django.db.models import Count, Q, Avg, Sum, F
from django.utils import timezone
from datetime import datetime, timedelta
from collections import Counter

from campaigns.models import Campaign, Question, Questionnaire
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, QuestionResponse, FollowUp
from accounts.models import User


def parse_date_range(request):
    """Parse date range from request GET params. Returns (start_date, end_date, label)."""
    preset = request.GET.get('date_range', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    today = timezone.localtime().date()

    if preset == 'today':
        return today, today, 'Today'
    elif preset == '7days':
        return today - timedelta(days=6), today, 'Last 7 Days'
    elif preset == '30days':
        return today - timedelta(days=29), today, 'Last 30 Days'
    elif preset == 'this_month':
        start = today.replace(day=1)
        return start, today, 'This Month'
    elif preset == 'last_month':
        first_of_this = today.replace(day=1)
        last_of_prev = first_of_this - timedelta(days=1)
        first_of_prev = last_of_prev.replace(day=1)
        return first_of_prev, last_of_prev, 'Last Month'
    elif preset == 'custom' and date_from and date_to:
        try:
            sd = datetime.strptime(date_from, '%Y-%m-%d').date()
            ed = datetime.strptime(date_to, '%Y-%m-%d').date()
            if sd > ed:
                sd, ed = ed, sd
            return sd, ed, 'Custom Range'
        except ValueError:
            pass

    # Default: no filter (all time)
    return None, None, 'All Time'


def get_filtered_calls(campaign_id=None, start_date=None, end_date=None, telecaller_id=None, call_status=None):
    """Return a filtered CallRecord queryset based on supplied criteria."""
    qs = CallRecord.objects.all()
    if campaign_id:
        qs = qs.filter(campaign_id=campaign_id)
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    if telecaller_id:
        qs = qs.filter(telecaller_id=telecaller_id)
    if call_status:
        qs = qs.filter(call_status=call_status)
    return qs


def compute_call_kpis(calls_qs):
    """Compute KPI metrics from a CallRecord queryset."""
    total_calls = calls_qs.count()
    completed = calls_qs.filter(call_status='Completed').count()
    completion_rate = round((completed / total_calls * 100), 1) if total_calls > 0 else 0
    avg_duration_sec = calls_qs.filter(call_status='Completed').aggregate(avg=Avg('duration'))['avg'] or 0
    avg_duration_sec = round(avg_duration_sec)

    # Format duration as Xm Ys
    mins = avg_duration_sec // 60
    secs = avg_duration_sec % 60
    avg_duration_fmt = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    # Unique customers contacted
    customers_contacted = calls_qs.values('customer').distinct().count()

    return {
        'total_calls': total_calls,
        'completed_calls': completed,
        'completion_rate': completion_rate,
        'avg_duration_sec': avg_duration_sec,
        'avg_duration_fmt': avg_duration_fmt,
        'customers_contacted': customers_contacted,
    }


def compute_call_outcome_counts(calls_qs):
    """Return call outcome counts as a dict."""
    statuses = ['Completed', 'No Answer', 'Unreachable', 'Busy', 'Follow-up Required']
    counts = {}
    total = calls_qs.count()
    for s in statuses:
        c = calls_qs.filter(call_status=s).count()
        pct = round((c / total * 100), 1) if total > 0 else 0
        counts[s] = {'count': c, 'pct': pct}
    return counts, total


def compute_call_activity_over_time(calls_qs, start_date, end_date):
    """Compute daily call counts for chart. Returns labels and data arrays."""
    if not start_date or not end_date:
        # Default to last 14 days
        end_date = timezone.localtime().date()
        start_date = end_date - timedelta(days=13)

    delta = (end_date - start_date).days
    # Cap at 60 days for readability
    if delta > 60:
        start_date = end_date - timedelta(days=59)
        delta = 59

    labels = []
    total_data = []
    completed_data = []

    current = start_date
    while current <= end_date:
        labels.append(current.strftime('%b %d'))
        day_calls = calls_qs.filter(created_at__date=current)
        total_data.append(day_calls.count())
        completed_data.append(day_calls.filter(call_status='Completed').count())
        current += timedelta(days=1)

    return labels, total_data, completed_data


def compute_campaign_performance(campaign_id=None, start_date=None, end_date=None):
    """Compute performance data for campaigns."""
    campaigns_qs = Campaign.objects.filter(status__in=['Active', 'Paused', 'Completed']).order_by('-created_at')
    if campaign_id:
        campaigns_qs = campaigns_qs.filter(id=campaign_id)

    results = []
    for camp in campaigns_qs[:12]:
        assigned_count = CampaignCustomer.objects.filter(campaign=camp).count()
        calls_filter = CallRecord.objects.filter(campaign=camp)
        if start_date:
            calls_filter = calls_filter.filter(created_at__date__gte=start_date)
        if end_date:
            calls_filter = calls_filter.filter(created_at__date__lte=end_date)

        completed_count = calls_filter.filter(call_status='Completed').count()
        target = camp.target_calls if camp.target_calls > 0 else assigned_count
        pending = max(0, target - completed_count)
        pct = round((completed_count / target * 100), 1) if target > 0 else 0
        if pct > 100:
            pct = 100.0

        results.append({
            'campaign': camp,
            'target': target,
            'assigned': assigned_count,
            'completed': completed_count,
            'pending': pending,
            'completion_pct': pct,
        })

    return results


def compute_telecaller_performance(campaign_id=None, start_date=None, end_date=None, telecaller_id=None):
    """Compute per-telecaller operational metrics."""
    telecallers = User.objects.filter(role='TELE_CALLER').order_by('first_name', 'username')
    if telecaller_id:
        telecallers = telecallers.filter(id=telecaller_id)
    results = []

    for tc in telecallers:
        assigned = CampaignCustomer.objects.filter(assigned_telecaller=tc)
        if campaign_id:
            assigned = assigned.filter(campaign_id=campaign_id)
        assigned_count = assigned.count()

        calls = get_filtered_calls(campaign_id=campaign_id, start_date=start_date, end_date=end_date, telecaller_id=tc.id)
        completed = calls.filter(call_status='Completed').count()
        total_calls = calls.count()
        pending = assigned.filter(assignment_status__in=['Assigned', 'In Progress']).count()

        avg_dur = calls.filter(call_status='Completed').aggregate(avg=Avg('duration'))['avg'] or 0
        avg_dur = round(avg_dur)
        mins = avg_dur // 60
        secs = avg_dur % 60
        avg_fmt = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        followups = FollowUp.objects.filter(assigned_to=tc, status__in=['Pending', 'Overdue'])
        if campaign_id:
            followups = followups.filter(call_record__campaign_id=campaign_id)
        fu_count = followups.count()

        comp_rate = round((completed / assigned_count * 100), 1) if assigned_count > 0 else 0

        results.append({
            'telecaller': tc,
            'assigned_customers': assigned_count,
            'total_calls': total_calls,
            'completed': completed,
            'completion_rate': comp_rate,
            'avg_duration': avg_fmt,
            'avg_duration_sec': avg_dur,
            'followups': fu_count,
            'pending': pending,
        })

    return results


def compute_questionnaire_analytics(campaign_id=None):
    """Compute per-question response analytics for questionnaire."""
    results = []
    campaign_obj = None

    if campaign_id:
        campaign_obj = Campaign.objects.filter(pk=campaign_id).first()

    if not campaign_obj:
        return results, None

    try:
        questionnaire = campaign_obj.questionnaire
    except Questionnaire.DoesNotExist:
        return results, campaign_obj

    questions = questionnaire.questions.all()
    for q in questions:
        resps = QuestionResponse.objects.filter(question=q, call_record__campaign=campaign_obj)
        total_resp = resps.count()
        q_info = {
            'question': q,
            'total_responses': total_resp,
            'counts': {},
            'avg_rating': None,
            'text_responses': [],
            'percentages': {},
        }

        if q.question_type in ['single_choice', 'yes_no', 'multiple_choice']:
            counts = {}
            for r in resps:
                for opt in r.selected_options:
                    counts[opt] = counts.get(opt, 0) + 1
            q_info['counts'] = counts
            if total_resp > 0:
                q_info['percentages'] = {k: round(v / total_resp * 100, 1) for k, v in counts.items()}
        elif q.question_type == 'rating_scale':
            avg_r = resps.aggregate(avg=Avg('rating'))['avg'] or 0
            q_info['avg_rating'] = round(avg_r, 2)
            q_info['counts'] = {str(i): resps.filter(rating=i).count() for i in range(1, 6)}
        elif q.question_type == 'open_ended':
            q_info['text_responses'] = list(
                resps.exclude(response_text='').values_list('response_text', flat=True)[:10]
            )

        results.append(q_info)

    return results, campaign_obj


def compute_customer_response_insights(campaign_id=None):
    """Derive aggregate insights from questionnaire responses."""
    insights = []
    resps_qs = QuestionResponse.objects.all().select_related('question')
    if campaign_id:
        resps_qs = resps_qs.filter(call_record__campaign_id=campaign_id)

    if not resps_qs.exists():
        return insights

    # Most selected option (across single_choice and multiple_choice)
    choice_responses = resps_qs.filter(
        question__question_type__in=['single_choice', 'multiple_choice', 'yes_no']
    )
    option_counter = Counter()
    for r in choice_responses:
        for opt in r.selected_options:
            option_counter[opt] = option_counter.get(opt, 0) + 1

    if option_counter:
        top_option, top_count = option_counter.most_common(1)[0]
        insights.append({
            'label': 'Most Selected Response',
            'value': f'"{top_option}"',
            'detail': f'{top_count} selections across all choice questions',
            'icon': 'bar-chart-2',
        })

    # Average rating across all rating questions
    rating_resps = resps_qs.filter(question__question_type='rating_scale', rating__isnull=False)
    if rating_resps.exists():
        avg_rating = rating_resps.aggregate(avg=Avg('rating'))['avg']
        if avg_rating:
            insights.append({
                'label': 'Average Importance Rating',
                'value': f'{round(avg_rating, 1)} / 5',
                'detail': f'Based on {rating_resps.count()} rating responses',
                'icon': 'star',
            })

    # Top open-ended themes (simple word frequency)
    open_resps = resps_qs.filter(
        question__question_type='open_ended'
    ).exclude(response_text='').values_list('response_text', flat=True)[:100]

    if open_resps:
        word_counter = Counter()
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 'of', 'to',
                      'in', 'for', 'on', 'with', 'as', 'it', 'at', 'by', 'this', 'that',
                      'i', 'we', 'they', 'he', 'she', 'not', 'but', 'be', 'have', 'has',
                      'do', 'does', 'did', 'will', 'can', 'could', 'would', 'should'}
        for text in open_resps:
            words = text.lower().split()
            for w in words:
                w = w.strip('.,!?;:"\'-()[]{}')
                if len(w) > 2 and w not in stop_words:
                    word_counter[w] += 1

        if word_counter:
            top_words = word_counter.most_common(3)
            themes_str = ', '.join([f'"{w}" ({c})' for w, c in top_words])
            insights.append({
                'label': 'Common Response Keywords',
                'value': top_words[0][0].title(),
                'detail': f'Top keywords: {themes_str}',
                'icon': 'message-circle',
            })

    return insights


def compute_followup_analytics(campaign_id=None, start_date=None, end_date=None):
    """Compute follow-up metrics and breakdowns."""
    fus = FollowUp.objects.all()
    if campaign_id:
        fus = fus.filter(call_record__campaign_id=campaign_id)
    if start_date:
        fus = fus.filter(scheduled_date__gte=start_date)
    if end_date:
        fus = fus.filter(scheduled_date__lte=end_date)

    total = fus.count()
    pending = fus.filter(status='Pending').count()
    overdue = fus.filter(status='Overdue').count()
    completed = fus.filter(status='Completed').count()
    cancelled = fus.filter(status='Cancelled').count()

    # By campaign
    by_campaign = []
    campaign_ids = fus.values_list('call_record__campaign', flat=True).distinct()
    for cid in campaign_ids:
        if cid is None:
            continue
        camp = Campaign.objects.filter(pk=cid).first()
        if camp:
            camp_fus = fus.filter(call_record__campaign=camp)
            by_campaign.append({
                'campaign': camp,
                'total': camp_fus.count(),
                'pending': camp_fus.filter(status='Pending').count(),
                'overdue': camp_fus.filter(status='Overdue').count(),
                'completed': camp_fus.filter(status='Completed').count(),
            })

    # By telecaller
    by_telecaller = []
    tc_ids = fus.values_list('assigned_to', flat=True).distinct()
    for tid in tc_ids:
        tc = User.objects.filter(pk=tid).first()
        if tc:
            tc_fus = fus.filter(assigned_to=tc)
            by_telecaller.append({
                'telecaller': tc,
                'total': tc_fus.count(),
                'pending': tc_fus.filter(status='Pending').count(),
                'overdue': tc_fus.filter(status='Overdue').count(),
                'completed': tc_fus.filter(status='Completed').count(),
            })

    return {
        'total': total,
        'pending': pending,
        'overdue': overdue,
        'completed': completed,
        'cancelled': cancelled,
        'by_campaign': by_campaign,
        'by_telecaller': by_telecaller,
    }
