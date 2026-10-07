from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect

import accounts.views as account_views
import campaigns.views as campaign_views
import customers.views as customer_views
import calls.views as call_views
import analytics.views as analytics_views

urlpatterns = [
    # Public Landing Page & Health Check
    path('', account_views.home_view, name='home'),
    path('health/', account_views.health_check, name='health_check'),

    # Auth
    path('login/', account_views.login_view, name='login'),
    path('register/', account_views.telecaller_register, name='telecaller_register'),
    path('logout/', account_views.logout_view, name='logout'),

    # Dashboard & Help Center
    path('dashboard/', analytics_views.dashboard, name='dashboard'),
    path('help/', account_views.help_center, name='help_center'),

    # Tele-callers Roster (Admin)
    path('tele-callers/', account_views.telecaller_list, name='telecaller_list'),
    path('tele-callers/create/', account_views.telecaller_create, name='telecaller_create'),
    path('tele-callers/<int:pk>/', account_views.telecaller_detail, name='telecaller_detail'),
    path('tele-callers/<int:pk>/edit/', account_views.telecaller_edit, name='telecaller_edit'),
    path('tele-callers/<int:pk>/reset-password/', account_views.telecaller_reset_password, name='telecaller_reset_password'),
    path('reset-password/<str:uidb64>/<str:token>/', account_views.user_password_reset_confirm, name='password_reset_confirm'),

    # Campaigns
    path('campaigns/', campaign_views.campaign_list, name='campaign_list'),
    path('campaigns/create/', campaign_views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/', campaign_views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/edit/', campaign_views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:pk>/status/', campaign_views.campaign_status_toggle, name='campaign_status_toggle'),
    path('campaigns/<int:pk>/delete/', campaign_views.campaign_delete, name='campaign_delete'),

    # Questionnaires
    path('questionnaires/<int:campaign_id>/builder/', campaign_views.questionnaire_builder, name='questionnaire_builder'),
    path('questionnaires/<int:campaign_id>/preview/', campaign_views.questionnaire_preview, name='questionnaire_preview'),

    # Customers
    path('customers/', customer_views.customer_list, name='customer_list'),
    path('customers/create/', customer_views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', customer_views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', customer_views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', customer_views.customer_delete, name='customer_delete'),
    path('customers/<int:pk>/restore/', customer_views.customer_restore, name='customer_restore'),
    path('customers/import/', customer_views.customer_import, name='customer_import'),
    path('customers/import/sample/', customer_views.customer_import_sample, name='customer_import_sample'),
    path('customers/assign/', customer_views.customer_assign, name='customer_assign'),
    path('customers/shift/', customer_views.customer_shift, name='customer_shift'),

    # Calls & Console
    path('calls/', call_views.call_list, name='call_list'),
    path('calls/record/<int:assignment_id>/', call_views.record_call, name='record_call'),
    path('calls/record/success/<int:call_id>/', call_views.call_success, name='call_success'),

    # Follow-ups
    path('followups/', call_views.followup_list, name='followup_list'),
    path('followups/<int:pk>/complete/', call_views.followup_complete, name='followup_complete'),
    path('followups/<int:pk>/cancel/', call_views.followup_cancel, name='followup_cancel'),
    path('followups/<int:pk>/reschedule/', call_views.followup_reschedule, name='followup_reschedule'),


    # Analytics & Reports
    path('analytics/', analytics_views.analytics_view, name='analytics'),
    path('analytics/api/chart-data/', analytics_views.chart_data_api, name='chart_data_api'),
    path('reports/', analytics_views.reports_view, name='reports'),
    path('reports/download/pdf/', analytics_views.export_pdf_report, name='export_pdf'),
    path('reports/download/excel/', analytics_views.export_excel_report, name='export_excel'),

    # Notifications
    path('notifications/', analytics_views.notification_list, name='notification_list'),
    path('notifications/read-all/', analytics_views.notification_read_all, name='notification_read_all'),
    path('notifications/<int:pk>/read/', analytics_views.notification_read_single, name='notification_read_single'),
]

# Custom Production Error Handlers
handler400 = 'accounts.views.custom_bad_request'
handler403 = 'accounts.views.custom_permission_denied'
handler404 = 'accounts.views.custom_page_not_found'
handler500 = 'accounts.views.custom_server_error'
