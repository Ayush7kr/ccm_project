from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date, time
import random

from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, QuestionResponse, FollowUp
from analytics.models import Notification

class Command(BaseCommand):
    help = 'Seeds realistic Indian demo data for CCM platform covering all UI states and workflows'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting comprehensive CCM database seeding..."))

        today = timezone.localtime().date()

        # 1. Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@ccm.local',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created or not admin_user.check_password('admin123'):
            admin_user.set_password('admin123')
            admin_user.save()

        self.stdout.write(self.style.SUCCESS("Admin account ready: admin / admin123"))

        # 2. Tele-callers with realistic Indian professional profiles
        telecallers = []
        tc_info = [
            ('rahul', 'Rahul', 'Sharma', 'rahul@ccm.local', '+91 98765 01001'),
            ('priya', 'Priya', 'Mehta', 'priya@ccm.local', '+91 98765 01002'),
            ('arjun', 'Arjun', 'Patil', 'arjun@ccm.local', '+91 98765 01003'),
            ('sneha', 'Sneha', 'Kulkarni', 'sneha@ccm.local', '+91 98765 01004'),
            ('telecaller1', 'Rohan', 'Gupta', 'rohan@ccm.local', '+91 98765 01005'),
        ]

        for uname, fname, lname, email, phone in tc_info:
            tc, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'first_name': fname,
                    'last_name': lname,
                    'phone': phone,
                    'role': 'TELE_CALLER'
                }
            )
            tc.set_password('telecaller123')
            tc.first_name = fname
            tc.last_name = lname
            tc.email = email
            tc.phone = phone
            tc.is_active = True
            tc.save()
            telecallers.append(tc)

        self.stdout.write(self.style.SUCCESS(f"Configured {len(telecallers)} Tele-callers."))

        # 3. Campaigns across distinct lifecycle statuses
        # Campaign 1: Active
        c1, _ = Campaign.objects.get_or_create(
            name="GST & Automated Invoicing Outreach",
            defaults={
                'description': "Qualifying MSME business owners for GST-compliant automated invoicing and accounting solutions.",
                'campaign_type': "Lead Generation",
                'start_date': today - timedelta(days=25),
                'end_date': today + timedelta(days=35),
                'status': 'Active',
                'target_calls': 50,
                'created_by': admin_user
            }
        )

        q1, _ = Questionnaire.objects.get_or_create(
            campaign=c1,
            defaults={
                'title': "GST Invoicing Qualification & Bottleneck Survey",
                'description': "Understand current invoicing software and GST filing bottlenecks.",
                'created_by': admin_user
            }
        )
        if not q1.questions.exists():
            Question.objects.create(
                questionnaire=q1,
                question_text="What billing method do you currently use for your daily invoicing?",
                question_type="single_choice",
                options=["Manual Paper Bills", "Excel Spreadsheets", "Tally / Legacy Software", "Third-party CA"],
                required=True,
                order=1
            )
            Question.objects.create(
                questionnaire=q1,
                question_text="What is your biggest friction point in daily GST compliance?",
                question_type="open_ended",
                required=False,
                order=2
            )
            Question.objects.create(
                questionnaire=q1,
                question_text="How important is instant WhatsApp/Email invoice sharing?",
                question_type="rating_scale",
                options=["1", "2", "3", "4", "5"],
                required=True,
                order=3
            )
            Question.objects.create(
                questionnaire=q1,
                question_text="Would you like a 15-minute live software demonstration?",
                question_type="yes_no",
                options=["Yes", "No"],
                required=True,
                order=4
            )
            Question.objects.create(
                questionnaire=q1,
                question_text="Which automation features are most critical to your team?",
                question_type="multiple_choice",
                options=["Automated E-way Bills", "Payment Gateway Links", "Multi-branch GST Reports", "Inventory Sync"],
                required=True,
                order=5
            )

        # Campaign 2: Active (Ending soon in 5 days to demonstrate Action Required card)
        c2, _ = Campaign.objects.get_or_create(
            name="Business Digital Presence & Website Audit",
            defaults={
                'description': "Evaluating website responsiveness and Google search ranking for retail and service enterprises.",
                'campaign_type': "Survey & Sales",
                'start_date': today - timedelta(days=20),
                'end_date': today + timedelta(days=5),
                'status': 'Active',
                'target_calls': 35,
                'created_by': admin_user
            }
        )

        q2, _ = Questionnaire.objects.get_or_create(
            campaign=c2,
            defaults={
                'title': "Digital Footprint & Lead Capture Survey",
                'description': "Assess current website status, Google Business profile, and digital inquiry channels.",
                'created_by': admin_user
            }
        )
        if not q2.questions.exists():
            Question.objects.create(
                questionnaire=q2,
                question_text="Does your business currently have a mobile-friendly website?",
                question_type="yes_no",
                options=["Yes", "No"],
                required=True,
                order=1
            )
            Question.objects.create(
                questionnaire=q2,
                question_text="How do prospective clients currently reach your business?",
                question_type="open_ended",
                required=False,
                order=2
            )
            Question.objects.create(
                questionnaire=q2,
                question_text="How would you rate the importance of Google Search visibility?",
                question_type="rating_scale",
                options=["1", "2", "3", "4", "5"],
                required=True,
                order=3
            )

        # Campaign 3: Paused
        c3, _ = Campaign.objects.get_or_create(
            name="Corporate Health & Employee Wellness Plan",
            defaults={
                'description': "Outreach to corporate HR heads for discounted annual employee medical checkups and insurance packages.",
                'campaign_type': "Corporate Wellness",
                'start_date': today - timedelta(days=15),
                'end_date': today + timedelta(days=40),
                'status': 'Paused',
                'target_calls': 30,
                'created_by': admin_user
            }
        )

        # Campaign 4: Draft
        c4, _ = Campaign.objects.get_or_create(
            name="Enterprise Cloud Storage & Disaster Recovery",
            defaults={
                'description': "Evaluating multi-cloud backup resilience for mid-sized IT and software exporters.",
                'campaign_type': "Technology",
                'start_date': today + timedelta(days=7),
                'end_date': today + timedelta(days=60),
                'status': 'Draft',
                'target_calls': 25,
                'created_by': admin_user
            }
        )

        # Campaign 5: Completed
        c5, _ = Campaign.objects.get_or_create(
            name="Retail POS Hardware Upgrade 2026",
            defaults={
                'description': "Hardware migration drive for merchant terminals to Android touch POS.",
                'campaign_type': "Hardware Upgrade",
                'start_date': today - timedelta(days=60),
                'end_date': today - timedelta(days=5),
                'status': 'Completed',
                'target_calls': 40,
                'created_by': admin_user
            }
        )

        # 4. Realistic Indian Customer Directory (30+ leads)
        customer_samples = [
            ("Apex Logistics India Pvt Ltd", "+919820011001", "contact@apexlogistics.in", "Apex Logistics", "Mumbai", "Maharashtra"),
            ("Sharma Traders & Wholesalers", "+919810022002", "info@sharmatraders.co.in", "Sharma Traders", "New Delhi", "Delhi"),
            ("Patil Earthmovers & Construction", "+919822033003", "sales@patilearth.com", "Patil Construction", "Pune", "Maharashtra"),
            ("Kulkarni Engineering Works", "+919823044004", "admin@kulkarniengg.com", "Kulkarni Engineering", "Nashik", "Maharashtra"),
            ("Mehta Financial Services", "+919845055005", "advisory@mehtafin.in", "Mehta Financial", "Bengaluru", "Karnataka"),
            ("Iyer Healthcare Solutions", "+919840066006", "support@iyerhealth.com", "Iyer Healthcare", "Chennai", "Tamil Nadu"),
            ("Reddy Infrastructure Ltd", "+919849077007", "projects@reddyinfra.com", "Reddy Infra", "Hyderabad", "Telangana"),
            ("Deshmukh Agro Foods", "+919821088008", "info@deshmukhagro.com", "Deshmukh Agro", "Nagpur", "Maharashtra"),
            ("Joshi Consulting Group", "+919890099009", "consult@joshigroup.in", "Joshi Consulting", "Pune", "Maharashtra"),
            ("Choudhury Textiles", "+919830012345", "orders@choudhurytex.com", "Choudhury Textiles", "Kolkata", "West Bengal"),
            ("Verma Electronics Store", "+919811023456", "sales@vermaelec.in", "Verma Electronics", "Noida", "Uttar Pradesh"),
            ("Nair Digital Media Agency", "+919847034567", "hello@nairdigital.com", "Nair Media", "Kochi", "Kerala"),
            ("Singh Auto Ancillaries", "+919814045678", "factory@singhauto.com", "Singh Auto", "Ludhiana", "Punjab"),
            ("Gupta Pharma Distributors", "+919827056789", "orders@guptapharma.in", "Gupta Pharma", "Indore", "Madhya Pradesh"),
            ("Rao Cold Storage & Logistics", "+919885067890", "dispatch@raocoldstorage.com", "Rao Logistics", "Vijayawada", "Andhra Pradesh"),
            ("Bhatt Renewable Energy", "+919825078901", "solar@bhattenergy.com", "Bhatt Energy", "Ahmedabad", "Gujarat"),
            ("Sengupta Publishing House", "+919831089012", "editor@senguptabooks.in", "Sengupta Publishing", "Kolkata", "West Bengal"),
            ("Kapoor Interior Studios", "+919818090123", "design@kapoorinteriors.com", "Kapoor Studios", "Gurugram", "Haryana"),
            ("Menon Hospitality & Resorts", "+919846001234", "bookings@menonresorts.com", "Menon Hospitality", "Trivandrum", "Kerala"),
            ("Agarwal Chemicals & Resins", "+919829012345", "sales@agarwalchem.com", "Agarwal Chem", "Jaipur", "Rajasthan"),
            ("Bose Marine Equipment", "+919832023456", "marine@boseequip.in", "Bose Marine", "Haldis", "West Bengal"),
            ("Chavhan Metal Crafts", "+919822134567", "info@chavhanmetals.com", "Chavhan Metals", "Kolhapur", "Maharashtra"),
            ("Pillai Packaging Systems", "+919841245678", "pack@pillaipack.com", "Pillai Packaging", "Coimbatore", "Tamil Nadu"),
            ("Trivedi Law Chambers", "+919879356789", "legal@trivedichambers.in", "Trivedi Law", "Vadodara", "Gujarat"),
            ("Wagle Food Processing", "+919820467890", "quality@waglefoods.com", "Wagle Foods", "Thane", "Maharashtra"),
            ("D'Souza Marine Supplies", "+919822556789", "info@dsouzamarine.in", "D'Souza Marine", "Panaji", "Goa"),
            ("Malhotra Sports Gear", "+919815667890", "sales@malhotrasports.com", "Malhotra Sports", "Jalandhar", "Punjab"),
            ("Sethi Precious Metals", "+919816778901", "admin@sethigold.in", "Sethi Metals", "Amritsar", "Punjab"),
            ("Grewal Dairy Farms", "+919817889012", "fresh@grewaldairy.com", "Grewal Dairy", "Chandigarh", "Punjab"),
            ("Bhatia Paper Mills", "+919826990123", "orders@bhatiatissue.com", "Bhatia Paper", "Bhopal", "Madhya Pradesh"),
            ("Unassigned Lead One", "+919899111222", "lead1@prospect.in", "Prospect Dynamics", "Gurugram", "Haryana"),
            ("Unassigned Lead Two", "+919899222333", "lead2@prospect.in", "Innovate Retail", "Mumbai", "Maharashtra"),
            ("Unassigned Lead Three", "+919899333444", "lead3@prospect.in", "Delta Express", "Bengaluru", "Karnataka"),
        ]

        customers = []
        for name, phone, email, company, city, state in customer_samples:
            cust, _ = Customer.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'email': email,
                    'company': company,
                    'city': city,
                    'state': state,
                    'source': 'Sample Seed'
                }
            )
            customers.append(cust)

        # 5. Assignments and Call History
        # Assign first 27 customers, leave last 3 as completely unassigned to trigger Action Required card
        assigned_customers = customers[:27]
        statuses = ['Completed', 'Completed', 'No Answer', 'Unreachable', 'Busy', 'Follow-up Required']

        for idx, cust in enumerate(assigned_customers):
            target_campaign = c1 if idx % 2 == 0 else c2
            target_telecaller = telecallers[idx % len(telecallers)]

            link, _ = CampaignCustomer.objects.get_or_create(
                campaign=target_campaign,
                customer=cust,
                defaults={
                    'assigned_telecaller': target_telecaller,
                    'assignment_status': 'In Progress',
                    'assigned_at': timezone.now() - timedelta(days=random.randint(1, 15))
                }
            )

            call_status = random.choice(statuses)
            duration_sec = random.randint(45, 380) if call_status == 'Completed' else random.randint(5, 30)
            start_t = timezone.now() - timedelta(hours=random.randint(1, 72))

            call_rec = CallRecord.objects.create(
                campaign=target_campaign,
                customer=cust,
                telecaller=target_telecaller,
                call_status=call_status,
                call_start_time=start_t,
                call_end_time=start_t + timedelta(seconds=duration_sec),
                duration=duration_sec,
                comments=f"Call with {cust.name} regarding {target_campaign.name}. Outcome disposition: {call_status}."
            )

            if call_status == 'Completed':
                link.assignment_status = 'Completed'
                link.save()

                # Questionnaire Responses
                target_q = q1 if target_campaign == c1 else q2
                for question in target_q.questions.all():
                    if question.question_type == 'single_choice':
                        QuestionResponse.objects.create(
                            call_record=call_rec,
                            question=question,
                            selected_options=[random.choice(question.options)]
                        )
                    elif question.question_type == 'rating_scale':
                        QuestionResponse.objects.create(
                            call_record=call_rec,
                            question=question,
                            rating=random.randint(3, 5)
                        )
                    elif question.question_type == 'yes_no':
                        QuestionResponse.objects.create(
                            call_record=call_rec,
                            question=question,
                            selected_options=[random.choice(['Yes', 'No'])]
                        )
                    elif question.question_type == 'multiple_choice':
                        opts_count = random.randint(1, min(2, len(question.options)))
                        QuestionResponse.objects.create(
                            call_record=call_rec,
                            question=question,
                            selected_options=random.sample(question.options, opts_count)
                        )
                    elif question.question_type == 'open_ended':
                        QuestionResponse.objects.create(
                            call_record=call_rec,
                            question=question,
                            response_text=f"Customer interested in feature demo for {cust.company}."
                        )

            elif call_status in ['Follow-up Required', 'No Answer']:
                # Distribute follow-ups into Overdue, Pending, and Completed
                fu_mode = idx % 3
                if fu_mode == 0:
                    fu_status = 'Overdue'
                    sched_date = today - timedelta(days=random.randint(1, 3))
                elif fu_mode == 1:
                    fu_status = 'Pending'
                    sched_date = today + timedelta(days=random.randint(0, 3))
                else:
                    fu_status = 'Completed'
                    sched_date = today - timedelta(days=random.randint(1, 2))

                sched_time = time(10 + (idx % 6), 30)
                if not FollowUp.objects.filter(customer=cust, scheduled_date=sched_date, scheduled_time=sched_time, status__in=['Pending', 'Overdue']).exists():
                    FollowUp.objects.create(
                        call_record=call_rec,
                        customer=cust,
                        assigned_to=target_telecaller,
                        scheduled_date=sched_date,
                        scheduled_time=sched_time,
                        status=fu_status,
                        notes=f"Callback required for {cust.name} regarding pricing terms."
                    )

        # 6. Diverse In-App Notifications
        for tc in telecallers:
            Notification.objects.create(
                recipient=tc,
                notification_type='assignment',
                title='Campaign Assignments Ready',
                message=f"You have active leads assigned in '{c1.name}'. Please check your task queue.",
                related_object_type='campaign',
                related_object_id=c1.id
            )
            Notification.objects.create(
                recipient=tc,
                notification_type='followup',
                title='Follow-up Callback Alert',
                message="You have a scheduled customer follow-up due on your workspace.",
                related_object_type='followup',
                related_object_id=None
            )

        Notification.objects.create(
            recipient=admin_user,
            notification_type='milestone',
            title='Campaign Milestone Achieved',
            message=f"'{c1.name}' has achieved 70%+ call completions!",
            related_object_type='campaign',
            related_object_id=c1.id
        )

        self.stdout.write(self.style.SUCCESS("CCM demo database successfully seeded with all realistic states!"))
