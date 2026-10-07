import csv
import io
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from datetime import timedelta, datetime

# PDF & Excel libraries
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import Notification
from accounts.models import User
from campaigns.models import Campaign, Question, Questionnaire
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, QuestionResponse, FollowUp
from accounts.decorators import admin_required

@login_required
def dashboard(request):
    """Main SaaS Dashboard View (Dispatches Admin vs Tele-caller)"""
    if request.user.is_admin_user:
        return admin_dashboard(request)
    else:
        return telecaller_dashboard(request)

def admin_dashboard(request):
    from calls.views import update_overdue_followups, check_inactive_telecallers
    update_overdue_followups()
    check_inactive_telecallers()

    total_campaigns = Campaign.objects.count()
    active_campaigns = Campaign.objects.filter(status='Active').count()
    total_customers = Customer.objects.count()
    calls_completed = CallRecord.objects.filter(call_status='Completed').count()
    calls_pending = CampaignCustomer.objects.filter(assignment_status__in=['Assigned', 'In Progress', 'Unassigned']).count()
    followups_due = FollowUp.objects.filter(status__in=['Pending', 'Overdue']).count()

    # Active Campaign Progress Tracker
    active_campaigns_qs = Campaign.objects.filter(status='Active').order_by('-created_at')[:6]
    campaign_progress_list = []
    for camp in active_campaigns_qs:
        assigned_count = CampaignCustomer.objects.filter(campaign=camp).count()
        completed_count = CallRecord.objects.filter(campaign=camp, call_status='Completed').count()
        target = camp.target_calls if camp.target_calls > 0 else assigned_count
        pending_count = max(0, (target if camp.target_calls > 0 else assigned_count) - completed_count)
        
        comp_pct = round((completed_count / target * 100), 1) if target > 0 else 0
        if comp_pct > 100:
            comp_pct = 100

        campaign_progress_list.append({
            'campaign': camp,
            'assigned_count': assigned_count,
            'completed_count': completed_count,
            'pending_count': pending_count,
            'target_calls': target,
            'progress_pct': comp_pct,
        })

    # Action Required Section items
    overdue_followups_count = FollowUp.objects.filter(status='Overdue').count()
    pending_calls_action_count = CampaignCustomer.objects.filter(assignment_status__in=['Assigned', 'In Progress']).count()
    unassigned_customers_count = Customer.objects.filter(
        Q(campaign_links__isnull=True) | Q(campaign_links__assignment_status='Unassigned')
    ).distinct().count()

    today = timezone.localtime().date()
    ending_soon_threshold = today + timedelta(days=7)
    campaigns_ending_soon_count = Campaign.objects.filter(
        status='Active',
        end_date__gte=today,
        end_date__lte=ending_soon_threshold
    ).count()

    action_required_items = []
    if overdue_followups_count > 0:
        action_required_items.append({
            'label': 'Overdue Follow-ups',
            'count': overdue_followups_count,
            'url': '/followups/?status=Overdue',
            'badge_class': 'badge-danger',
            'icon': 'alert-triangle'
        })
    if pending_calls_action_count > 0:
        action_required_items.append({
            'label': 'Pending Calls',
            'count': pending_calls_action_count,
            'url': '/customers/?status=Assigned',
            'badge_class': 'badge-warning',
            'icon': 'clock'
        })
    if unassigned_customers_count > 0:
        action_required_items.append({
            'label': 'Unassigned Customers',
            'count': unassigned_customers_count,
            'url': '/customers/assign/',
            'badge_class': 'badge-info',
            'icon': 'user-plus'
        })
    if campaigns_ending_soon_count > 0:
        action_required_items.append({
            'label': 'Campaigns Ending Soon',
            'count': campaigns_ending_soon_count,
            'url': '/campaigns/?status=Active',
            'badge_class': 'badge-secondary',
            'icon': 'calendar'
        })

    # Chart 1 Data: Call Status breakdown (pre-computed for template use)
    calls_completed_count = CallRecord.objects.filter(call_status='Completed').count()
    calls_no_answer_count = CallRecord.objects.filter(call_status='No Answer').count()
    calls_unreachable_count = CallRecord.objects.filter(call_status='Unreachable').count()
    calls_busy_count = CallRecord.objects.filter(call_status='Busy').count()
    calls_followup_count = CallRecord.objects.filter(call_status='Follow-up Required').count()

    # Chart 2 Data: Telecaller Performance
    telecaller_stats = User.objects.filter(role='TELE_CALLER').annotate(
        completed=Count('call_records', filter=Q(call_records__call_status='Completed')),
        total=Count('call_records')
    )
    telecaller_stats_list = list(telecaller_stats)
    telecaller_chart_labels = json.dumps([tc.username for tc in telecaller_stats_list])
    telecaller_chart_data = json.dumps([tc.completed for tc in telecaller_stats_list])

    # Recent items
    recent_calls = CallRecord.objects.all().select_related('customer', 'telecaller', 'campaign')[:8]
    pending_followups = FollowUp.objects.filter(status='Pending').select_related('customer', 'assigned_to')[:5]

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'total_customers': total_customers,
        'calls_completed': calls_completed,
        'calls_pending': calls_pending,
        'followups_due': followups_due,
        'campaign_progress_list': campaign_progress_list,
        'action_required_items': action_required_items,
        # Individual status counts for charts
        'chart_completed': calls_completed_count,
        'chart_no_answer': calls_no_answer_count,
        'chart_unreachable': calls_unreachable_count,
        'chart_busy': calls_busy_count,
        'chart_followup': calls_followup_count,
        'telecaller_stats': telecaller_stats,
        'telecaller_chart_labels': telecaller_chart_labels,
        'telecaller_chart_data': telecaller_chart_data,
        'recent_calls': recent_calls,
        'pending_followups': pending_followups
    })

def telecaller_dashboard(request):
    from calls.views import update_overdue_followups
    update_overdue_followups(request.user)

    user = request.user
    assigned_links = CampaignCustomer.objects.filter(
        assigned_telecaller=user,
        campaign__status='Active'
    ).select_related('customer', 'campaign')
    
    assigned_customers = assigned_links.count()
    calls_completed = CallRecord.objects.filter(telecaller=user, call_status='Completed').count()
    calls_pending = assigned_links.filter(assignment_status__in=['Assigned', 'In Progress']).count()
    followups_due = FollowUp.objects.filter(assigned_to=user, status__in=['Pending', 'Overdue']).count()
    
    today = timezone.localtime().date()
    todays_calls = CallRecord.objects.filter(telecaller=user, created_at__date=today).count()
    completed_today = CallRecord.objects.filter(telecaller=user, call_status='Completed', created_at__date=today).count()

    # Build "My Next Tasks" combining urgent callbacks and next queue leads
    next_tasks = []
    followup_customer_ids = set()

    # 1. Scheduled follow-ups (Pending or Overdue)
    today_followups = FollowUp.objects.filter(
        assigned_to=user,
        status__in=['Pending', 'Overdue']
    ).select_related('customer', 'call_record__campaign').order_by('scheduled_date', 'scheduled_time')[:10]

    for fu in today_followups:
        camp = fu.call_record.campaign if fu.call_record else None
        # Find the assignment link for this customer (any status — we just need the campaign reference)
        link = CampaignCustomer.objects.filter(
            customer=fu.customer, assigned_telecaller=user, campaign__status='Active'
        ).first()

        due_str = f"{fu.scheduled_time.strftime('%I:%M %p')}" if fu.scheduled_time else "Anytime"
        if fu.status == 'Overdue':
            due_str = f"Overdue ({fu.scheduled_date.strftime('%b %d')})"

        campaign_obj = camp or (link.campaign if link else None)

        # Determine whether the assignment allows a new call or is completed
        assignment_status = link.assignment_status if link else None
        can_start_call = assignment_status in ('Assigned', 'In Progress') if link else False

        # Build action based on assignment state
        if can_start_call and link:
            # Assignment is still open — follow-up call goes through normal record_call
            action_label = 'Start Follow-up Call'
            action_url_name = 'record_call'
            action_pk = link.pk
            task_type = 'followup_call'
        else:
            # Assignment is completed — follow-up should be handled via follow-up workflow
            action_label = 'Handle Follow-up'
            action_url_name = 'followup_list'
            action_pk = None
            task_type = 'followup_only'

        followup_customer_ids.add(fu.customer_id)
        next_tasks.append({
            'customer': fu.customer,
            'campaign': campaign_obj,
            'task': 'Follow-up Callback',
            'due_time': due_str,
            'is_urgent': True,
            'assignment_pk': action_pk,
            'status': fu.status,
            'task_type': task_type,
            'action_label': action_label,
            'action_url_name': action_url_name,
            'followup_id': fu.pk,
        })

    # 2. General pending customer calling queue (only Assigned/In Progress)
    pending_leads = assigned_links.filter(
        assignment_status__in=['Assigned', 'In Progress']
    ).exclude(customer_id__in=followup_customer_ids)[:15]

    for link in pending_leads:
        action_label = 'Continue Call' if link.assignment_status == 'In Progress' else 'Start Call'
        next_tasks.append({
            'customer': link.customer,
            'campaign': link.campaign,
            'task': 'Call Customer',
            'due_time': 'Next in Queue',
            'is_urgent': False,
            'assignment_pk': link.pk,
            'status': link.assignment_status,
            'task_type': 'new_call',
            'action_label': action_label,
            'action_url_name': 'record_call',
            'followup_id': None,
        })

    return render(request, 'dashboard/telecaller_dashboard.html', {
        'assigned_customers': assigned_customers,
        'calls_completed': calls_completed,
        'calls_pending': calls_pending,
        'followups_due': followups_due,
        'todays_calls': todays_calls,
        'completed_today': completed_today,
        'next_tasks': next_tasks[:20]
    })


# --- ANALYTICS & CHART API ---

@admin_required
def analytics_view(request):
    from .engine import (parse_date_range, get_filtered_calls, compute_call_kpis,
                         compute_call_outcome_counts, compute_call_activity_over_time,
                         compute_campaign_performance, compute_telecaller_performance,
                         compute_questionnaire_analytics, compute_customer_response_insights,
                         compute_followup_analytics)

    campaign_id = request.GET.get('campaign', '')
    start_date, end_date, date_label = parse_date_range(request)
    campaigns = Campaign.objects.all().order_by('name')

    # Build filtered call queryset
    calls_qs = get_filtered_calls(
        campaign_id=campaign_id or None,
        start_date=start_date,
        end_date=end_date,
    )

    # KPIs
    kpis = compute_call_kpis(calls_qs)

    # Follow-up count (filtered)
    followup_qs = FollowUp.objects.all()
    if campaign_id:
        followup_qs = followup_qs.filter(call_record__campaign_id=campaign_id)
    if start_date:
        followup_qs = followup_qs.filter(scheduled_date__gte=start_date)
    if end_date:
        followup_qs = followup_qs.filter(scheduled_date__lte=end_date)
    kpis['followups'] = followup_qs.count()

    # Positive responses (ratings >= 4)
    positive_qs = QuestionResponse.objects.filter(
        question__question_type='rating_scale', rating__gte=4
    )
    if campaign_id:
        positive_qs = positive_qs.filter(call_record__campaign_id=campaign_id)
    if start_date:
        positive_qs = positive_qs.filter(call_record__created_at__date__gte=start_date)
    if end_date:
        positive_qs = positive_qs.filter(call_record__created_at__date__lte=end_date)
    kpis['positive_responses'] = positive_qs.count()

    # Call outcome breakdown
    outcome_counts, outcome_total = compute_call_outcome_counts(calls_qs)

    # Call activity over time
    activity_labels, activity_total, activity_completed = compute_call_activity_over_time(
        calls_qs, start_date, end_date
    )

    # Campaign performance
    campaign_perf = compute_campaign_performance(
        campaign_id=campaign_id or None,
        start_date=start_date,
        end_date=end_date,
    )

    # Telecaller performance
    tc_perf = compute_telecaller_performance(
        campaign_id=campaign_id or None,
        start_date=start_date,
        end_date=end_date,
    )

    # Questionnaire analytics (only when campaign selected)
    question_analytics, selected_campaign_obj = compute_questionnaire_analytics(
        campaign_id=campaign_id or None
    )

    # Customer response insights
    response_insights = compute_customer_response_insights(
        campaign_id=campaign_id or None
    )

    # Follow-up analytics
    fu_analytics = compute_followup_analytics(
        campaign_id=campaign_id or None,
        start_date=start_date,
        end_date=end_date,
    )

    # Date range display
    if start_date and end_date:
        date_display = f"{start_date.strftime('%b %d, %Y')} — {end_date.strftime('%b %d, %Y')}"
    else:
        date_display = 'All Time'

    # Active filters flag
    has_filters = bool(campaign_id or start_date or request.GET.get('date_range'))

    return render(request, 'analytics/analytics.html', {
        'campaigns': campaigns,
        'selected_campaign': campaign_id,
        'selected_campaign_obj': selected_campaign_obj,
        'date_range': request.GET.get('date_range', ''),
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
        'date_label': date_label,
        'date_display': date_display,
        'has_filters': has_filters,
        # KPIs
        'kpis': kpis,
        # Outcome breakdown
        'outcome_counts': outcome_counts,
        'outcome_total': outcome_total,
        'outcome_chart_data': json.dumps([d['count'] for d in outcome_counts.values()]),
        # Activity over time (JSON for charts)
        'activity_labels': json.dumps(activity_labels),
        'activity_total': json.dumps(activity_total),
        'activity_completed': json.dumps(activity_completed),
        # Campaign performance
        'campaign_perf': campaign_perf,
        # Telecaller performance
        'tc_perf': tc_perf,
        # Questionnaire analytics
        'question_analytics': question_analytics,
        # Customer insights
        'response_insights': response_insights,
        # Follow-up analytics
        'fu_analytics': fu_analytics,
    })


@admin_required
def chart_data_api(request):
    from .engine import (parse_date_range, get_filtered_calls,
                         compute_call_outcome_counts, compute_call_activity_over_time)

    campaign_id = request.GET.get('campaign_id')
    start_date, end_date, _ = parse_date_range(request)

    calls = get_filtered_calls(
        campaign_id=campaign_id or None,
        start_date=start_date,
        end_date=end_date,
    )

    # Status Distribution
    outcome_counts, outcome_total = compute_call_outcome_counts(calls)
    statuses = ['Completed', 'No Answer', 'Unreachable', 'Busy', 'Follow-up Required']
    status_counts = [outcome_counts[s]['count'] for s in statuses]

    # Activity over time
    activity_labels, activity_total, activity_completed = compute_call_activity_over_time(
        calls, start_date, end_date
    )

    # Telecaller comparison
    telecallers = User.objects.filter(role='TELE_CALLER')
    tc_labels = [tc.get_full_name() or tc.username for tc in telecallers]
    tc_calls = calls if calls else CallRecord.objects.none()
    tc_completed = []
    for tc in telecallers:
        tc_completed.append(tc_calls.filter(telecaller=tc, call_status='Completed').count())

    return JsonResponse({
        'status_labels': statuses,
        'status_counts': status_counts,
        'activity_labels': activity_labels,
        'activity_total': activity_total,
        'activity_completed': activity_completed,
        'telecaller_labels': tc_labels,
        'telecaller_completed': tc_completed,
    })


# --- REPORTING ENGINE (PDF & EXCEL) ---

@admin_required
def reports_view(request):
    from .engine import parse_date_range, get_filtered_calls

    campaigns = Campaign.objects.all().order_by('name')
    telecallers = User.objects.filter(role='TELE_CALLER').order_by('first_name', 'username')

    # Preview counts
    report_type = request.GET.get('report_type', '')
    campaign_id = request.GET.get('campaign', '')
    telecaller_id = request.GET.get('telecaller', '')
    call_status = request.GET.get('call_status', '')
    start_date, end_date, date_label = parse_date_range(request)

    preview = None
    if report_type:
        preview = _build_report_preview(
            report_type, campaign_id, telecaller_id, call_status, start_date, end_date, date_label
        )

    return render(request, 'reports/reports.html', {
        'campaigns': campaigns,
        'telecallers': telecallers,
        'report_type': report_type,
        'selected_campaign': campaign_id,
        'selected_telecaller': telecaller_id,
        'selected_status': call_status,
        'date_range': request.GET.get('date_range', ''),
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
        'date_label': date_label,
        'preview': preview,
    })


def _build_report_preview(report_type, campaign_id, telecaller_id, call_status, start_date, end_date, date_label):
    """Build a preview summary for the report before generation."""
    from .engine import get_filtered_calls

    preview = {
        'report_type': report_type,
        'report_label': {
            'campaign': 'Campaign Summary Report',
            'calls': 'Call Activity Report',
            'responses': 'Customer Response Report',
            'telecaller': 'Tele-caller Activity Report',
            'followups': 'Follow-up Report',
        }.get(report_type, report_type.title()),
        'campaign_name': 'All Campaigns',
        'telecaller_name': 'All Tele-callers',
        'date_range': date_label,
        'record_count': 0,
    }

    if campaign_id:
        camp = Campaign.objects.filter(pk=campaign_id).first()
        preview['campaign_name'] = camp.name if camp else f'Campaign #{campaign_id}'

    if telecaller_id:
        tc = User.objects.filter(pk=telecaller_id).first()
        preview['telecaller_name'] = (tc.get_full_name() or tc.username) if tc else f'User #{telecaller_id}'

    if report_type == 'campaign':
        qs = Campaign.objects.all()
        if campaign_id:
            qs = qs.filter(pk=campaign_id)
        preview['record_count'] = qs.count()
        preview['record_label'] = 'campaigns'
    elif report_type == 'calls':
        qs = get_filtered_calls(campaign_id or None, start_date, end_date, telecaller_id or None, call_status or None)
        preview['record_count'] = qs.count()
        preview['record_label'] = 'call records'
    elif report_type == 'responses':
        qs = QuestionResponse.objects.all()
        if campaign_id:
            qs = qs.filter(call_record__campaign_id=campaign_id)
        if telecaller_id:
            qs = qs.filter(call_record__telecaller_id=telecaller_id)
        if start_date:
            qs = qs.filter(call_record__created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(call_record__created_at__date__lte=end_date)
        preview['record_count'] = qs.count()
        preview['record_label'] = 'responses'
    elif report_type == 'telecaller':
        tc_qs = User.objects.filter(role='TELE_CALLER')
        if telecaller_id:
            tc_qs = tc_qs.filter(id=telecaller_id)
        preview['record_count'] = tc_qs.count()
        preview['record_label'] = 'tele-callers'
    elif report_type == 'followups':
        qs = FollowUp.objects.all()
        if campaign_id:
            qs = qs.filter(call_record__campaign_id=campaign_id)
        if telecaller_id:
            qs = qs.filter(assigned_to_id=telecaller_id)
        if call_status:
            qs = qs.filter(status=call_status)
        if start_date:
            qs = qs.filter(scheduled_date__gte=start_date)
        if end_date:
            qs = qs.filter(scheduled_date__lte=end_date)
        preview['record_count'] = qs.count()
        preview['record_label'] = 'follow-ups'

    if start_date and end_date:
        preview['date_display'] = f"{start_date.strftime('%b %d, %Y')} — {end_date.strftime('%b %d, %Y')}"
    else:
        preview['date_display'] = 'All Time'

    return preview


@admin_required
def export_pdf_report(request):
    from .engine import parse_date_range, get_filtered_calls, compute_call_kpis

    report_type = request.GET.get('report_type', 'campaign')
    campaign_id = request.GET.get('campaign')
    telecaller_id = request.GET.get('telecaller')
    call_status_filter = request.GET.get('call_status')
    start_date, end_date, date_label = parse_date_range(request)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22,
                                 textColor=colors.HexColor('#0f172a'))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=10,
                                    textColor=colors.HexColor('#64748b'), spaceAfter=6)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=13, leading=16,
                                   textColor=colors.HexColor('#1e293b'), spaceBefore=14, spaceAfter=8)

    report_labels = {
        'campaign': 'Campaign Summary Report',
        'calls': 'Call Activity Report',
        'responses': 'Customer Response Report',
        'telecaller': 'Tele-caller Activity Report',
        'followups': 'Follow-up Report',
    }
    report_label = report_labels.get(report_type, report_type.title() + ' Report')

    # Header
    story.append(Paragraph("CCM — Campaign Call Manager", title_style))
    story.append(Paragraph(report_label, ParagraphStyle('ReportTitle', parent=styles['Heading2'],
                           fontSize=14, textColor=colors.HexColor('#2563eb'), spaceAfter=4)))
    story.append(Paragraph(f"Generated: {timezone.localtime().strftime('%B %d, %Y at %I:%M %p IST')}", subtitle_style))

    # Filters line
    filter_parts = []
    if campaign_id:
        camp = Campaign.objects.filter(pk=campaign_id).first()
        filter_parts.append(f"Campaign: {camp.name if camp else campaign_id}")
    if telecaller_id:
        tc = User.objects.filter(pk=telecaller_id).first()
        filter_parts.append(f"Tele-caller: {(tc.get_full_name() or tc.username) if tc else telecaller_id}")
    if call_status_filter:
        filter_parts.append(f"Status: {call_status_filter}")
    if start_date and end_date:
        filter_parts.append(f"Period: {start_date.strftime('%b %d, %Y')} — {end_date.strftime('%b %d, %Y')}")
    else:
        filter_parts.append(f"Period: {date_label}")
    if filter_parts:
        story.append(Paragraph(" | ".join(filter_parts), subtitle_style))
    story.append(Spacer(1, 12))

    # Common table style
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])

    if report_type == 'campaign':
        # Summary KPIs
        calls_qs = get_filtered_calls(campaign_id or None, start_date, end_date)
        kpis = compute_call_kpis(calls_qs)
        story.append(Paragraph("Summary", section_style))
        kpi_data = [
            ["Total Calls", "Completed", "Completion Rate", "Avg Duration", "Customers Contacted"],
            [str(kpis['total_calls']), str(kpis['completed_calls']),
             f"{kpis['completion_rate']}%", kpis['avg_duration_fmt'], str(kpis['customers_contacted'])]
        ]
        kpi_table = Table(kpi_data, colWidths=[100, 90, 100, 90, 120])
        kpi_table.setStyle(table_style)
        story.append(kpi_table)
        story.append(Spacer(1, 12))

        campaigns_qs = Campaign.objects.all()
        if campaign_id:
            campaigns_qs = campaigns_qs.filter(id=campaign_id)

        story.append(Paragraph("Campaign Details", section_style))
        data = [["Campaign", "Type", "Status", "Start", "End", "Target", "Completed", "Completion %"]]
        for c in campaigns_qs:
            comp = CallRecord.objects.filter(campaign=c, call_status='Completed').count()
            target = c.target_calls if c.target_calls > 0 else CampaignCustomer.objects.filter(campaign=c).count()
            pct = f"{round(comp/target*100, 1)}%" if target > 0 else "0%"
            data.append([c.name[:25], c.campaign_type[:12], c.status,
                        str(c.start_date), str(c.end_date), str(target), str(comp), pct])

        t = Table(data, colWidths=[95, 65, 50, 65, 65, 45, 55, 55])
        t.setStyle(table_style)
        story.append(t)

    elif report_type == 'calls':
        calls_qs = get_filtered_calls(campaign_id or None, start_date, end_date, telecaller_id or None, call_status_filter or None)
        kpis = compute_call_kpis(calls_qs)

        story.append(Paragraph("Summary", section_style))
        kpi_data = [
            ["Total Calls", "Completed", "Completion Rate", "Avg Duration"],
            [str(kpis['total_calls']), str(kpis['completed_calls']),
             f"{kpis['completion_rate']}%", kpis['avg_duration_fmt']]
        ]
        kpi_table = Table(kpi_data, colWidths=[120, 120, 120, 120])
        kpi_table.setStyle(table_style)
        story.append(kpi_table)
        story.append(Spacer(1, 12))

        story.append(Paragraph("Call Records", section_style))
        calls = calls_qs.select_related('customer', 'campaign', 'telecaller')[:200]
        data = [["Customer", "Campaign", "Tele-caller", "Status", "Duration", "Date"]]
        for cl in calls:
            data.append([cl.customer.name[:18], cl.campaign.name[:15], cl.telecaller.username[:12],
                        cl.call_status, f"{cl.duration}s",
                        cl.created_at.strftime('%Y-%m-%d') if cl.created_at else ''])

        t = Table(data, colWidths=[90, 90, 75, 85, 55, 70])
        t.setStyle(table_style)
        story.append(t)

    elif report_type == 'responses':
        story.append(Paragraph("Customer Response Data", section_style))
        responses = QuestionResponse.objects.all().select_related(
            'question', 'call_record__customer', 'call_record__campaign')
        if campaign_id:
            responses = responses.filter(call_record__campaign_id=campaign_id)
        if telecaller_id:
            responses = responses.filter(call_record__telecaller_id=telecaller_id)
        if start_date:
            responses = responses.filter(call_record__created_at__date__gte=start_date)
        if end_date:
            responses = responses.filter(call_record__created_at__date__lte=end_date)

        data = [["Customer", "Question", "Type", "Response"]]
        for r in responses[:200]:
            ans = ""
            if r.question.question_type in ['single_choice', 'yes_no', 'multiple_choice']:
                ans = ", ".join(r.selected_options)
            elif r.question.question_type == 'rating_scale':
                ans = f"{r.rating}/5"
            else:
                ans = r.response_text[:35]
            data.append([r.call_record.customer.name[:18], r.question.question_text[:30],
                        r.question.get_question_type_display()[:15], ans[:30]])

        t = Table(data, colWidths=[90, 160, 90, 160])
        t.setStyle(table_style)
        story.append(t)

    elif report_type == 'followups':
        story.append(Paragraph("Follow-up Schedule Report", section_style))
        followups = FollowUp.objects.all().select_related('customer', 'assigned_to', 'call_record__campaign')
        if campaign_id:
            followups = followups.filter(call_record__campaign_id=campaign_id)
        if telecaller_id:
            followups = followups.filter(assigned_to_id=telecaller_id)
        if call_status_filter:
            followups = followups.filter(status=call_status_filter)
        if start_date:
            followups = followups.filter(scheduled_date__gte=start_date)
        if end_date:
            followups = followups.filter(scheduled_date__lte=end_date)

        # Status summary
        total_fu = followups.count()
        pending_fu = followups.filter(status='Pending').count()
        overdue_fu = followups.filter(status='Overdue').count()
        completed_fu = followups.filter(status='Completed').count()
        kpi_data = [
            ["Total", "Pending", "Overdue", "Completed"],
            [str(total_fu), str(pending_fu), str(overdue_fu), str(completed_fu)]
        ]
        kpi_table = Table(kpi_data, colWidths=[120, 120, 120, 120])
        kpi_table.setStyle(table_style)
        story.append(kpi_table)
        story.append(Spacer(1, 10))

        data = [["Customer", "Tele-caller", "Campaign", "Date", "Time", "Status"]]
        for fu in followups[:200]:
            camp_name = fu.call_record.campaign.name[:15] if fu.call_record and fu.call_record.campaign else 'N/A'
            data.append([fu.customer.name[:18], fu.assigned_to.username[:12], camp_name,
                        str(fu.scheduled_date), str(fu.scheduled_time)[:5], fu.status])

        t = Table(data, colWidths=[90, 80, 90, 75, 55, 65])
        t.setStyle(table_style)
        story.append(t)

    else:  # telecaller
        story.append(Paragraph("Tele-caller Performance Report", section_style))
        from .engine import compute_telecaller_performance
        tc_perf = compute_telecaller_performance(campaign_id or None, start_date, end_date, telecaller_id=telecaller_id or None)

        data = [["Name", "Username", "Assigned", "Completed", "Completion %", "Avg Duration", "Pending", "Follow-ups"]]
        for row in tc_perf:
            tc = row['telecaller']
            data.append([
                tc.get_full_name() or tc.username, tc.username,
                str(row['assigned_customers']), str(row['completed']),
                f"{row['completion_rate']}%", row['avg_duration'],
                str(row['pending']), str(row['followups'])
            ])

        t = Table(data, colWidths=[85, 65, 55, 60, 60, 65, 50, 55])
        t.setStyle(table_style)
        story.append(t)

    # Page number footer
    story.append(Spacer(1, 20))
    story.append(Paragraph("— End of Report —", ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=1)))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ccm_{report_type}_report.pdf"'
    return response


@admin_required
def export_excel_report(request):
    from .engine import parse_date_range, get_filtered_calls, compute_call_kpis, compute_telecaller_performance

    report_type = request.GET.get('report_type', 'campaign')
    campaign_id = request.GET.get('campaign')
    telecaller_id = request.GET.get('telecaller')
    call_status_filter = request.GET.get('call_status')
    start_date, end_date, date_label = parse_date_range(request)

    wb = openpyxl.Workbook()

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_align = Alignment(horizontal='center', vertical='center')
    date_font = Font(name="Calibri", size=9, color="64748B")
    summary_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    summary_font = Font(name="Calibri", size=10, bold=True)
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0'),
    )

    def style_header_row(ws, row_num=1):
        for cell in ws[row_num]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

    def auto_width(ws):
        for col_idx in range(1, ws.max_column + 1):
            col_letter = get_column_letter(col_idx)
            max_len = 0
            for row_idx in range(1, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(min(max_len + 4, 40), 12)

    report_labels = {
        'campaign': 'Campaign Summary',
        'calls': 'Call Activity',
        'responses': 'Customer Responses',
        'telecaller': 'Telecaller Performance',
        'followups': 'Follow-up Schedule',
    }

    if report_type == 'campaign':
        # Summary sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        calls_qs = get_filtered_calls(campaign_id or None, start_date, end_date)
        kpis = compute_call_kpis(calls_qs)
        ws_summary.append(["CCM — Campaign Summary Report"])
        ws_summary.merge_cells('A1:E1')
        ws_summary['A1'].font = Font(name="Calibri", size=14, bold=True)
        ws_summary.append([f"Generated: {timezone.localtime().strftime('%B %d, %Y %I:%M %p IST')}"])
        ws_summary['A2'].font = date_font
        ws_summary.append([f"Period: {date_label}"])
        ws_summary['A3'].font = date_font
        ws_summary.append([])
        ws_summary.append(["Total Calls", "Completed", "Completion Rate", "Avg Duration", "Customers Contacted"])
        style_header_row(ws_summary, 5)
        ws_summary.append([kpis['total_calls'], kpis['completed_calls'],
                          f"{kpis['completion_rate']}%", kpis['avg_duration_fmt'], kpis['customers_contacted']])
        for cell in ws_summary[6]:
            cell.fill = summary_fill
            cell.font = summary_font
        ws_summary.append([])

        # Campaign data sheet
        ws_data = wb.create_sheet("Campaign Details")
        headers = ["Campaign Name", "Type", "Status", "Start Date", "End Date", "Target Calls", "Completed Calls", "Completion %"]
        ws_data.append(headers)
        style_header_row(ws_data)

        c_qs = Campaign.objects.all()
        if campaign_id:
            c_qs = c_qs.filter(id=campaign_id)
        for c in c_qs:
            comp = CallRecord.objects.filter(campaign=c, call_status='Completed').count()
            target = c.target_calls if c.target_calls > 0 else CampaignCustomer.objects.filter(campaign=c).count()
            pct = f"{round(comp/target*100, 1)}%" if target > 0 else "0%"
            ws_data.append([c.name, c.campaign_type, c.status, str(c.start_date), str(c.end_date), target, comp, pct])
        auto_width(ws_data)
        auto_width(ws_summary)

    elif report_type == 'calls':
        ws = wb.active
        ws.title = "Call Activity"
        headers = ["Customer Name", "Phone", "Campaign", "Tele-caller", "Call Status", "Duration (sec)", "Date"]
        ws.append(headers)
        style_header_row(ws)

        calls_qs = get_filtered_calls(campaign_id or None, start_date, end_date, telecaller_id or None, call_status_filter or None)
        calls_qs = calls_qs.select_related('customer', 'campaign', 'telecaller')
        for cl in calls_qs[:500]:
            ws.append([cl.customer.name, cl.customer.phone, cl.campaign.name,
                      cl.telecaller.username, cl.call_status, cl.duration,
                      cl.created_at.strftime('%Y-%m-%d %H:%M') if cl.created_at else ''])
        auto_width(ws)

    elif report_type == 'responses':
        ws = wb.active
        ws.title = "Customer Responses"
        headers = ["Customer", "Phone", "Campaign", "Question", "Type", "Response"]
        ws.append(headers)
        style_header_row(ws)

        resps_qs = QuestionResponse.objects.all().select_related(
            'question', 'call_record__customer', 'call_record__campaign')
        if campaign_id:
            resps_qs = resps_qs.filter(call_record__campaign_id=campaign_id)
        if telecaller_id:
            resps_qs = resps_qs.filter(call_record__telecaller_id=telecaller_id)
        if start_date:
            resps_qs = resps_qs.filter(call_record__created_at__date__gte=start_date)
        if end_date:
            resps_qs = resps_qs.filter(call_record__created_at__date__lte=end_date)

        for r in resps_qs[:500]:
            ans = ""
            if r.question.question_type in ['single_choice', 'yes_no', 'multiple_choice']:
                ans = ", ".join(r.selected_options)
            elif r.question.question_type == 'rating_scale':
                ans = f"{r.rating}/5"
            else:
                ans = r.response_text
            ws.append([r.call_record.customer.name, r.call_record.customer.phone,
                      r.call_record.campaign.name, r.question.question_text,
                      r.question.get_question_type_display(), ans])
        auto_width(ws)

    elif report_type == 'followups':
        ws = wb.active
        ws.title = "Follow-up Schedule"
        headers = ["Customer", "Phone", "Tele-caller", "Campaign", "Scheduled Date", "Time", "Status", "Notes"]
        ws.append(headers)
        style_header_row(ws)

        fus = FollowUp.objects.all().select_related('customer', 'assigned_to', 'call_record__campaign')
        if campaign_id:
            fus = fus.filter(call_record__campaign_id=campaign_id)
        if telecaller_id:
            fus = fus.filter(assigned_to_id=telecaller_id)
        if call_status_filter:
            fus = fus.filter(status=call_status_filter)
        if start_date:
            fus = fus.filter(scheduled_date__gte=start_date)
        if end_date:
            fus = fus.filter(scheduled_date__lte=end_date)

        for fu in fus[:500]:
            camp_name = fu.call_record.campaign.name if fu.call_record and fu.call_record.campaign else 'N/A'
            ws.append([fu.customer.name, fu.customer.phone, fu.assigned_to.username, camp_name,
                      str(fu.scheduled_date), str(fu.scheduled_time)[:5], fu.status, fu.notes[:50] if fu.notes else ''])
        auto_width(ws)

    else:  # telecaller
        ws = wb.active
        ws.title = "Telecaller Performance"
        headers = ["Name", "Username", "Email", "Assigned Customers", "Completed Calls",
                   "Completion Rate", "Avg Duration", "Pending Calls", "Follow-ups"]
        ws.append(headers)
        style_header_row(ws)

        tc_perf = compute_telecaller_performance(campaign_id or None, start_date, end_date, telecaller_id=telecaller_id or None)
        for row in tc_perf:
            tc = row['telecaller']
            ws.append([tc.get_full_name() or tc.username, tc.username, tc.email,
                      row['assigned_customers'], row['completed'],
                      f"{row['completion_rate']}%", row['avg_duration'],
                      row['pending'], row['followups']])
        auto_width(ws)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(output.getvalue(),
                           content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="ccm_{report_type}_export.xlsx"'
    return response

# --- NOTIFICATIONS CENTER ---

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user)
    return render(request, 'notifications/list.html', {
        'notifications': notifications
    })

@login_required
def notification_read_all(request):
    if request.method != 'POST':
        return redirect('notification_list')
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notification_list')

@login_required
def notification_read_single(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if request.method == 'POST':
        notif.is_read = True
        notif.save()

    # Smart redirect to relevant object if present, with graceful handling for deleted or unassigned objects
    if notif.related_object_type == 'campaign' and notif.related_object_id:
        camp = Campaign.objects.filter(pk=notif.related_object_id).first()
        if camp:
            if request.user.is_admin_user or CampaignCustomer.objects.filter(campaign=camp, assigned_telecaller=request.user).exists():
                return redirect('campaign_detail', pk=camp.pk)
            else:
                messages.info(request, "You are no longer assigned to this campaign.")
        else:
            messages.info(request, "The related campaign is no longer available.")
    elif notif.related_object_type == 'customer' and notif.related_object_id:
        cust = Customer.objects.filter(pk=notif.related_object_id).first()
        if cust:
            if request.user.is_admin_user or CampaignCustomer.objects.filter(customer=cust, assigned_telecaller=request.user).exists():
                return redirect('customer_detail', pk=cust.pk)
            else:
                messages.info(request, "You do not have access to this customer.")
        else:
            messages.info(request, "The related customer is no longer available.")
    elif notif.related_object_type == 'followup':
        return redirect('followup_list')

    return redirect('notification_list')

