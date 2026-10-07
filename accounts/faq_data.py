"""
Role-based FAQ and Help Center Knowledge Base for CCM (Campaign Call Manager).
Strictly matches actual CCM system behavior and permissions.
"""

ADMIN_FAQ_CATEGORIES = [
    {
        'id': 'getting-started',
        'title': 'Getting Started',
        'icon': 'compass',
        'description': 'Overview of CCM platform capabilities and administrator controls.',
        'questions': [
            {
                'q': 'What is CCM?',
                'a': (
                    'Campaign Call Manager (CCM) is an enterprise outbound tele-calling and lead lifecycle platform. '
                    'It enables organizations to organize marketing campaigns, import customer leads, allocate workload to '
                    'tele-callers, capture live call outcomes and questionnaire responses, schedule callbacks, and track unified analytics.'
                )
            },
            {
                'q': 'What can an Administrator do?',
                'a': (
                    'Administrators have full operational authority: creating and managing campaigns, configuring custom scripts '
                    'via the Questionnaire Builder, importing customer contacts (CSV/Excel), assigning unassigned leads to tele-callers, '
                    'shifting lead ownership between tele-callers, managing the tele-caller roster and passwords, monitoring '
                    'unified analytics, and exporting reports in PDF and Excel.'
                )
            },
            {
                'q': 'How do I navigate the Admin dashboard?',
                'a': (
                    'The Admin Dashboard displays key KPI cards (Total Calls, Completed Calls, Pending Workload, Overdue Callbacks), '
                    'a fast action toolbar (New Campaign, Tele-callers Roster, Import Customers, Assign Workload), an Active Campaigns '
                    'table with target progress percentages, and a Tele-caller Performance summary.'
                )
            }
        ]
    },
    {
        'id': 'campaign-management',
        'title': 'Campaign Management',
        'icon': 'megaphone',
        'description': 'Creating, updating, and monitoring marketing and tele-calling campaigns.',
        'questions': [
            {
                'q': 'How do I create a campaign?',
                'a': (
                    'Go to Campaigns in the sidebar and click "+ Create Campaign". Enter the campaign name, description, '
                    'campaign type (default is Tele-calling), target call volume, and start and end dates. '
                    'New campaigns can be set to Draft or Active status.'
                )
            },
            {
                'q': 'How do I edit campaign details?',
                'a': (
                    'From the Campaigns directory, click "View" on any campaign card to open its detail page, then click '
                    '"Edit Campaign". You can update its name, description, target call volume, status (Draft, Active, Paused, '
                    'Completed, Archived), and timeframe.'
                )
            },
            {
                'q': 'How do I view campaign progress?',
                'a': (
                    'Open the campaign detail page. The Overview tab displays progress against target calls (cleanly capped at 100%), '
                    'total enrolled leads, assigned leads, unassigned leads, completed calls, and pending callbacks. You can also inspect '
                    'the Enrolled Customers tab to monitor individual lead statuses.'
                )
            },
            {
                'q': 'How do I manage campaign questionnaires?',
                'a': (
                    'From the campaign detail page, click "Questionnaire Builder". If no questionnaire exists, one will be initialized. '
                    'You can add questions, reorder questions, configure answer options, specify question types, and preview how the '
                    'script renders in the live call console.'
                )
            }
        ]
    },
    {
        'id': 'customer-management',
        'title': 'Customer Management & Assignment',
        'icon': 'users',
        'description': 'Lead directory, CSV/Excel import, lead assignment, and workload shifting.',
        'questions': [
            {
                'q': 'How do I upload/import customers?',
                'a': (
                    'Navigate to Customers → "Import Customers". Upload a `.csv` or `.xlsx` spreadsheet. Required columns are `name` '
                    'and `phone`. Optional columns include `whatsapp_number`, `email`, `company`, `address`, `city`, `state`, and `notes`. '
                    'You can select a target campaign to automatically enroll leads. An interactive preview lets you verify row data before importing.'
                )
            },
            {
                'q': 'How are customers assigned to tele-callers?',
                'a': (
                    'Navigate to Customers → "Assign Customers" (or click "Assign Customers" inside any campaign). '
                    'Select the target campaign and an active tele-caller agent, select leads from the unassigned list using checkboxes, '
                    'and click "Assign Selected". The agent immediately receives an in-app assignment notification.'
                )
            },
            {
                'q': 'Why are already-assigned customers not shown in the normal assignment list?',
                'a': (
                    'To prevent accidental double-assignment, the "Assign Customers" selectable list displays ONLY active unassigned leads. '
                    'Already-assigned and completed leads are excluded from new assignment. Both frontend filtering and backend server-side '
                    'validation reject attempts to reassign an already-assigned lead through standard assignment.'
                )
            },
            {
                'q': 'How do I shift a customer from one tele-caller to another?',
                'a': (
                    'On the Assign Customers page, scroll to the "CURRENTLY ASSIGNED CUSTOMERS — SHIFT WORKLOAD" section. '
                    'Select the destination tele-caller (must be an active tele-caller), check one or multiple currently assigned leads, '
                    'and click "Shift Customer". The system verifies that the destination is not the same tele-caller and updates lead ownership.'
                )
            },
            {
                'q': 'What happens to historical call records when a customer is shifted?',
                'a': (
                    'Historical call ownership is strictly protected. Shifting a customer updates future assignment ownership '
                    '(`CampaignCustomer.assigned_telecaller`), but NEVER rewrites or modifies past `CallRecord` logs. Prior calls, '
                    'durations, notes, and questionnaire responses stay permanently associated with the original tele-caller who placed them.'
                )
            }
        ]
    },
    {
        'id': 'questionnaire-management',
        'title': 'Questionnaire Management',
        'icon': 'file-question',
        'description': 'Building call scripts, configuring question types, and validating responses.',
        'questions': [
            {
                'q': 'How do I create questions?',
                'a': (
                    'Open the campaign detail page and click "Questionnaire Builder". In the question form, enter the question prompt, '
                    'select the question type, enter comma-separated choices if applicable, toggle the "Required" flag, and click "Save Question".'
                )
            },
            {
                'q': 'What question types are supported?',
                'a': (
                    'CCM supports 5 question types: 1) Single Choice (radio options), 2) Multiple Choice (checkboxes), '
                    '3) Rating Scale (1 to 5 stars), 4) Open Ended (multiline text area), and 5) Yes / No (binary choices).'
                )
            },
            {
                'q': 'How do I mark a question as required?',
                'a': (
                    'Check the "Required" toggle when creating or editing a question. Required questions are validated server-side: '
                    'when a tele-caller sets the call outcome to "Completed", all required questions must have valid answers before the call can be saved.'
                )
            },
            {
                'q': 'How does a questionnaire become available to a tele-caller?',
                'a': (
                    'As soon as a questionnaire is configured for an active campaign, it automatically renders inside Section 3 '
                    '("Campaign Call Script & Questionnaire") of the live Call Console for any lead assigned in that campaign.'
                )
            }
        ]
    },
    {
        'id': 'analytics-reports',
        'title': 'Analytics & Reports',
        'icon': 'bar-chart-2',
        'description': 'Unified analytics engine, date filters, performance tables, and document exports.',
        'questions': [
            {
                'q': 'What metrics are available?',
                'a': (
                    'CCM computes 100% database-derived unified metrics across the dashboard, analytics view, and exports: '
                    'Total Calls, Completed Calls, Pending Workload, Overdue Callbacks, Average Call Duration, Call Outcome Distribution, '
                    'and Call Activity Trends.'
                )
            },
            {
                'q': 'How does campaign completion work?',
                'a': (
                    'Campaign progress percentage is computed as `(completed_calls / target_calls) * 100`. '
                    'The value is capped at 100.0% to reflect progress against the milestone without overflow.'
                )
            },
            {
                'q': 'How do I view tele-caller performance?',
                'a': (
                    'Navigate to Analytics in the sidebar. The Tele-caller Performance Table summarizes total calls logged, '
                    'completed calls, conversion percentage, and average call duration for each agent, with date range filtering.'
                )
            },
            {
                'q': 'How do I generate/export reports?',
                'a': (
                    'Navigate to Reports in the sidebar. Choose one of the 5 report types (Campaign Summary, Call Activity, '
                    'Tele-caller Performance, Customer Response, or Follow-up Schedule), apply filters (date range, campaign, agent, status), '
                    'preview the record count, and click "Export PDF" for styled ReportLab documents or "Export Excel" for openpyxl workbooks.'
                )
            }
        ]
    },
    {
        'id': 'telecaller-management',
        'title': 'Tele-caller Management',
        'icon': 'user-check',
        'description': 'Managing agent accounts, roster permissions, and workload oversight.',
        'questions': [
            {
                'q': 'How do I manage tele-callers?',
                'a': (
                    'Navigate to Tele-callers in the sidebar. Administrators can view the roster, register new tele-callers via '
                    '"+ Add Tele-caller", edit agent details, activate/deactivate accounts, and trigger password reset links.'
                )
            },
            {
                'q': 'How are customers assigned?',
                'a': (
                    'Lead assignment is performed on the Customers → "Assign Customers" page. Admins choose the campaign, '
                    'select the designated active tele-caller, check unassigned leads, and commit the assignment.'
                )
            },
            {
                'q': 'What permissions does a tele-caller have?',
                'a': (
                    'Tele-callers have restricted operational access: they can view only their assigned leads and campaigns, '
                    'launch the live Call Console for assigned leads, answer questionnaires, manage their own follow-ups, and review '
                    'their own call logs. They cannot create campaigns, edit questionnaires, reassign leads, view other agents’ records, or access admin reports.'
                )
            }
        ]
    },
    {
        'id': 'notifications',
        'title': 'System Notifications',
        'icon': 'bell',
        'description': 'Milestone alerts, inactive agent notifications, and notification lifecycle.',
        'questions': [
            {
                'q': 'What do system notifications mean?',
                'a': (
                    'Administrators receive high-priority alerts when a campaign reaches 70% of its target call volume (milestone alert), '
                    'and operational alerts when an active tele-caller with assigned leads has logged zero calls in the past 7 days (inactive agent alert).'
                )
            },
            {
                'q': 'How do I mark notifications as read?',
                'a': (
                    'Click the bell icon in the top navbar to view unread alerts in the dropdown, or click "View All" to go to the Notifications '
                    'center. Click any notification to mark it as read and jump to the relevant item, or click "Mark All as Read".'
                )
            }
        ]
    }
]

TELECALLER_FAQ_CATEGORIES = [
    {
        'id': 'getting-started',
        'title': 'Getting Started',
        'icon': 'compass',
        'description': 'Your workspace overview, assigned workload, and daily workflow.',
        'questions': [
            {
                'q': 'What can I do as a tele-caller?',
                'a': (
                    'As a tele-caller in CCM, you can view your assigned campaigns and customer leads, conduct live calls using the '
                    'Call Console stopwatch, record call dispositions and conversation notes, answer campaign questionnaires, '
                    'schedule and complete follow-up callbacks, and review your personal call history.'
                )
            },
            {
                'q': 'How do I view my assigned customers?',
                'a': (
                    'Click "Customer Directory" in the sidebar. Tele-callers see only the customer leads currently assigned to them. '
                    'You can also view your pending call workload directly from the Tele-caller Dashboard task queue.'
                )
            },
            {
                'q': 'How do I view my campaigns?',
                'a': (
                    'Navigate to Campaigns in the sidebar. You will see active campaigns where you currently have assigned leads, '
                    'including your assigned lead count and completed call progress.'
                )
            }
        ]
    },
    {
        'id': 'customer-campaigns',
        'title': 'Customer Leads & Campaigns',
        'icon': 'users',
        'description': 'Understanding lead access, assignment visibility, and workload transfers.',
        'questions': [
            {
                'q': 'How do I view my assigned customers?',
                'a': (
                    'Open the Customer Directory or open any of your assigned campaigns under Campaigns → "Enrolled Customers". '
                    'Each customer card shows their phone number, optional WhatsApp link, email, company, and current assignment status.'
                )
            },
            {
                'q': 'Why can’t I see a particular customer?',
                'a': (
                    'CCM enforces strict role-based access control (RBAC). Tele-callers can only view leads assigned to their account. '
                    'If a customer is not assigned to you or belongs to another agent, you will not have access. Contact your administrator '
                    'if you need a customer assigned to you.'
                )
            },
            {
                'q': 'What happens if a customer is shifted to me?',
                'a': (
                    'When an administrator shifts a lead to you, an in-app assignment notification is automatically sent to your account. '
                    'The customer will immediately appear in your assigned directory and dashboard task queue ready for dialing.'
                )
            }
        ]
    },
    {
        'id': 'call-console',
        'title': 'Live Call Console & Logging',
        'icon': 'phone-call',
        'description': 'Dialing workflow, stopwatch controls, outcome dispositions, and call notes.',
        'questions': [
            {
                'q': 'How do I start a customer call?',
                'a': (
                    'From your Dashboard task queue or Customer Directory, click "Start Call" next to an assigned lead. '
                    'This opens the live Call Console with the customer profile, contact details, live stopwatch, outcome selector, '
                    'and campaign call script.'
                )
            },
            {
                'q': 'How do I record a call outcome?',
                'a': (
                    'Select the appropriate disposition from the "Select Call Outcome Status" dropdown: '
                    '✓ Call Completed & Questionnaire Answered, ✕ No Answer / Ringing, ✕ Unreachable / Switched Off, '
                    '✕ Line Busy / Call Waiting, or 🕒 Follow-up Required. Enter call notes and click "Save Call Log".'
                )
            },
            {
                'q': 'What is the difference between Completed, No Answer, and Unreachable?',
                'a': (
                    'Use "Completed" when you successfully spoke with the contact and completed the questionnaire script. '
                    'Use "No Answer" if the call rang out without pickup. Use "Unreachable" if the phone was disconnected, switched off, '
                    'or out of coverage. Use "Busy" if the line was engaged. Use "Follow-up Required" if the contact requested a callback.'
                )
            },
            {
                'q': 'How do I add call notes?',
                'a': (
                    'Enter discussion highlights, customer objections, or context for future callbacks in the '
                    '"Call Conversation Notes & Objections" field in the Call Console.'
                )
            },
            {
                'q': 'How does the call stopwatch work?',
                'a': (
                    'The stopwatch begins automatically when you enter the Call Console. You can Pause, Resume, or Reset the timer '
                    'using the buttons. When you save the call log, the duration is recorded in seconds.'
                )
            }
        ]
    },
    {
        'id': 'questionnaire',
        'title': 'Campaign Questionnaire Script',
        'icon': 'file-question',
        'description': 'Answering campaign survey questions during live calls.',
        'questions': [
            {
                'q': 'Where can I find the campaign questionnaire?',
                'a': (
                    'The questionnaire is displayed in Section 3 ("Campaign Call Script & Questionnaire") of the Call Console. '
                    'It remains visible while you speak so you can read the script and capture answers in real time.'
                )
            },
            {
                'q': 'How do I answer different question types?',
                'a': (
                    'CCM supports 5 question types: '
                    '1) Single Choice: select one radio button; '
                    '2) Multiple Choice: check all relevant boxes; '
                    '3) Rating Scale: click a 1–5 star rating button; '
                    '4) Open Ended: type notes in the text area; '
                    '5) Yes / No: click the Yes or No button.'
                )
            },
            {
                'q': 'What happens if a required question is unanswered?',
                'a': (
                    'If you choose the "Completed" outcome, all required questions (marked with * Required) must be answered. '
                    'If any required question is missing, the system will highlight it in red and block saving until completed. '
                    'For non-connected outcomes (No Answer, Busy, Unreachable), questionnaire answers are optional.'
                )
            },
            {
                'q': 'Where are my questionnaire responses saved?',
                'a': (
                    'Responses are saved securely in the database and tied directly to the created call record. '
                    'They appear in the customer’s Interaction History timeline.'
                )
            }
        ]
    },
    {
        'id': 'follow-ups',
        'title': 'Follow-ups & Callbacks',
        'icon': 'calendar',
        'description': 'Scheduling, handling overdue callbacks, rescheduling, and resolution.',
        'questions': [
            {
                'q': 'How do I schedule a follow-up?',
                'a': (
                    'In the Call Console, check "Enable Callback" (or select "Follow-up Required" status). '
                    'Specify the scheduled callback date and time, add a callback reason, and submit the call log.'
                )
            },
            {
                'q': 'How do I handle an overdue follow-up?',
                'a': (
                    'Follow-ups past their scheduled date and time automatically display as "Overdue" with amber/red badges. '
                    'From your Dashboard or Follow-ups page, click "Handle Follow-up" to start the callback, or use the action menu '
                    'to reschedule or mark complete.'
                )
            },
            {
                'q': 'How do I reschedule a follow-up?',
                'a': (
                    'On the Follow-ups page, click the action button and select "Reschedule". Enter the updated callback date '
                    'and time and save.'
                )
            },
            {
                'q': 'How do I cancel/complete a follow-up?',
                'a': (
                    'In the Follow-ups list, click "Mark Complete" when the callback has been satisfied, or select "Cancel Callback" '
                    'from the action menu if the follow-up is no longer required.'
                )
            }
        ]
    },
    {
        'id': 'call-history',
        'title': 'Call History & Privacy',
        'icon': 'history',
        'description': 'Reviewing past calls and understanding customer privacy boundaries.',
        'questions': [
            {
                'q': 'How do I view previous calls?',
                'a': (
                    'Navigate to Call History in the sidebar. You can search by customer name, filter by campaign, or filter by call outcome '
                    'to review all calls you have previously logged.'
                )
            },
            {
                'q': 'Can I see calls made by other tele-callers?',
                'a': (
                    'No. Tele-callers can only see their own call logs. Records created by other agents are hidden to maintain '
                    'agent privacy and avoid cross-workload interference.'
                )
            },
            {
                'q': 'Why can’t I access another tele-caller’s customers?',
                'a': (
                    'CCM enforces strict server-side RBAC. Even if an assignment ID is manually entered in the browser URL, '
                    'the system will reject access and redirect you back with an "Access denied" warning.'
                )
            }
        ]
    },
    {
        'id': 'notifications',
        'title': 'Notifications',
        'icon': 'bell',
        'description': 'Workload alerts, callback reminders, and notification management.',
        'questions': [
            {
                'q': 'How do assignment notifications work?',
                'a': (
                    'Whenever an administrator assigns new leads to you or shifts leads to your roster, you receive an in-app '
                    'notification detailing the campaign and lead count.'
                )
            },
            {
                'q': 'How do I open a new assignment notification?',
                'a': (
                    'Click the notification bell icon in the top navigation bar. Clicking on an assignment alert takes you directly '
                    'to the corresponding campaign details.'
                )
            },
            {
                'q': 'How do I mark notifications as read?',
                'a': (
                    'Clicking any notification in the dropdown or on the Notifications page marks it as read. '
                    'You can also click "Mark All as Read" on the Notifications page to clear all badges at once.'
                )
            }
        ]
    }
]

GENERAL_FAQ_CATEGORY = {
    'id': 'general-ccm',
    'title': 'General CCM Platform',
    'icon': 'help-circle',
    'description': 'Common questions about system usage, themes, and accounts.',
    'questions': [
        {
            'q': 'How do I switch between Dark and Light mode?',
            'a': (
                'Click the Moon / Sun icon in the top navigation header at any time. CCM immediately toggles between light and '
                'dark themes and persists your preference across sessions in your browser storage.'
            )
        },
        {
            'q': 'Which browsers are supported?',
            'a': (
                'CCM is fully compatible with all modern standards-compliant web browsers, including Google Chrome, Mozilla Firefox, '
                'Microsoft Edge, and Apple Safari, across desktop, tablet, and mobile screen sizes.'
            )
        },
        {
            'q': 'How do I log out of my account?',
            'a': (
                'Click the "Logout" link at the bottom of the left sidebar. Your session will be securely terminated and you will be '
                'redirected to the login page.'
            )
        }
    ]
}


def get_faqs_for_user(user):
    """
    Returns role-filtered FAQ categories for an authenticated user.
    Strictly prevents tele-callers from receiving Admin-only FAQ categories.
    """
    if not user or not user.is_authenticated:
        return []

    if getattr(user, 'is_admin_user', False) or user.role == 'ADMIN':
        return ADMIN_FAQ_CATEGORIES + [GENERAL_FAQ_CATEGORY]
    elif getattr(user, 'is_telecaller_user', False) or user.role == 'TELE_CALLER':
        return TELECALLER_FAQ_CATEGORIES + [GENERAL_FAQ_CATEGORY]

    return [GENERAL_FAQ_CATEGORY]
