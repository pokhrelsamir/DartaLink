"""Create demo staff and sample requests in every workflow state.

    python manage.py seed_demo            # add demo data (idempotent for users)
    python manage.py seed_demo --reset    # delete existing requests first
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Department, Role, StaffProfile, User
from requests_app.models import AdministrativeRequest, Status
from workflow.models import WorkflowLog
from workflow.services import perform

# username, first, last, role, dept code, designation
DEMO_USERS = [
    ("admin", "System", "Administrator", Role.SYSADMIN, None, "System Administrator"),
    ("karyalaya", "Ramesh", "Adhikari", Role.KARYALAYA_PRAMUKH, "KP", "Office Head"),
    ("prabidhik", "Sunita", "Gurung", Role.PRABIDHIK_PRAMUKH, "PP", "Chief Engineer"),
    ("lekha", "Bishnu", "Sharma", Role.LEKHA_PRAMUKH, "LP", "Chief Accounts Officer"),
    ("rajaswa", "Kamala", "Thapa", Role.RAJASWA_PRAMUKH, "RS", "Revenue Section Chief"),
    ("budget", "Prakash", "Koirala", Role.BUDGET_PRAMUKH, "BS", "Budget Section Chief"),
    ("itchief", "Anita", "Rai", Role.IT_PRAMUKH, "IT", "IT Section Chief"),
    ("darta1", "Sita", "Poudel", Role.DARTA_STAFF, "DT", "Darta Officer"),
    ("darta2", "Hari", "Bhandari", Role.DARTA_STAFF, "DT", "Darta Assistant"),
    ("chalani1", "Gita", "Karki", Role.CHALANI_STAFF, "CH", "Chalani Officer"),
    ("chalani2", "Binod", "Shrestha", Role.CHALANI_STAFF, "CH", "Chalani Assistant"),
    ("it_staff", "Nabin", "Lama", Role.STAFF, "IT", "System Engineer"),
    ("it_staff2", "Mina", "Tamang", Role.STAFF, "IT", "Network Technician"),
    ("rev_staff", "Deepak", "Joshi", Role.STAFF, "RS", "Revenue Officer"),
    ("tech_staff", "Rojina", "Basnet", Role.STAFF, "PP", "Engineer"),
]


class Command(BaseCommand):
    help = "Create demo users and sample requests."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all existing requests first.")

    @transaction.atomic
    def handle(self, *args, **opts):
        pw = settings.DEMO_PASSWORD
        if opts["reset"]:
            AdministrativeRequest.objects.all().delete()
        users = {}
        for username, first, last, role, code, desig in DEMO_USERS:
            dept = Department.objects.get(code=code) if code else None
            user, created = User.objects.get_or_create(username=username, defaults={
                "first_name": first, "last_name": last, "role": role, "department": dept,
                "email": f"{username}@dartalink.example", "is_staff": role == Role.SYSADMIN,
                "is_superuser": role == Role.SYSADMIN})
            if created:
                user.set_password(pw)
                user.save()
                StaffProfile.objects.filter(user=user).update(designation=desig, office_location="Pokhara Office",
                                                              phone="9800000000")
            users[username] = user

        if AdministrativeRequest.objects.exists():
            self.stdout.write("Requests already exist - skipping sample requests (use --reset to rebuild).")
        else:
            self._requests(users)
        self.stdout.write(self.style.SUCCESS(f"Demo data ready. Password for every demo user: {pw}"))
        self.stdout.write("Staff IDs: " + ", ".join(f"{u.username}={u.staff_id}" for u in users.values()))

    # ---------------------------------------------------------------
    def _mk(self, user, title, category, priority, description, amount=None):
        req = AdministrativeRequest.objects.create(
            title=title, category=category, priority=priority, description=description,
            requested_amount=amount, requester=user, department=user.department, status=Status.DRAFT)
        WorkflowLog.objects.create(request=req, action="create", to_status=Status.DRAFT, actor=user,
                                   from_department=user.department, remarks="Draft created")
        return req

    def _requests(self, u):
        P = perform
        kp, pp, lp = u["karyalaya"], u["prabidhik"], u["lekha"]
        d, c = u["darta1"], u["chalani1"]
        it_dept = Department.objects.get(code="IT")
        lp_dept = Department.objects.get(code="LP")
        pp_dept = Department.objects.get(code="PP")

        # 1 draft
        self._mk(u["it_staff"], "Replacement laptop for network operations", "PROCUREMENT", "NORMAL",
                 "Current laptop is five years old and cannot run the monitoring tools.", 145000)
        # 2 submitted, waiting for the IT section head
        r = self._mk(u["it_staff2"], "Request for VPN access for remote maintenance", "IT_SUPPORT", "HIGH",
                     "Need secure VPN access to the Pokhara distribution nodes for after-hours maintenance.")
        P(r, u["it_staff2"], "submit")
        # 3 verified, waiting for Darta
        r = self._mk(u["rev_staff"], "Annual leave application - 12 days", "LEAVE", "NORMAL",
                     "Annual leave from 2083 Kartik 10 to Kartik 22 for family travel.")
        P(r, u["rev_staff"], "submit"); P(r, u["rajaswa"], "verify")
        # 4 returned for revision
        r = self._mk(u["tech_staff"], "Training on fibre splicing", "TRAINING", "LOW",
                     "Requesting nomination for the fibre splicing course in Kathmandu.", 38000)
        P(r, u["tech_staff"], "submit"); P(r, u["prabidhik"], "return", {"remarks": "Attach the course invitation letter and cost estimate."})
        # 5 registered, waiting to be forwarded
        r = self._mk(u["it_staff"], "Server room air-conditioner repair", "MAINTENANCE", "URGENT",
                     "Primary AC unit failed; temperature is above safe limits for the racks.", 62000)
        P(r, u["it_staff"], "submit"); P(r, u["itchief"], "verify"); P(r, d, "register", {"remarks": "Urgent - registered same day."})
        # 6 forwarded to Lekha (in authority inbox)
        r = self._mk(u["rev_staff"], "Advance for field revenue audit", "BUDGET", "NORMAL",
                     "Travel advance for the quarterly revenue audit of three service centres.", 54000)
        P(r, u["rev_staff"], "submit"); P(r, u["rajaswa"], "verify"); P(r, d, "register")
        P(r, d, "forward", {"to_department": lp_dept.pk, "remarks": "Please verify the budget head."})
        # 7 under review (recommendation + tippani), now with Karyalaya Pramukh
        r = self._mk(u["it_staff"], "Procure 10 managed switches", "PROCUREMENT", "HIGH",
                     "Managed switches are needed to replace failed units in the Lakeside exchange.", 380000)
        P(r, u["it_staff"], "submit"); P(r, u["itchief"], "verify"); P(r, d, "register")
        P(r, d, "forward", {"to_department": pp_dept.pk})
        P(r, pp, "recommend", {"remarks": "Technically justified. Specifications match the standard."})
        P(r, pp, "tippani", {"remarks": "Forwarded to Office Head for decision. Budget exists under the capital head."})
        P(r, pp, "forward", {"to_department": Department.objects.get(code="KP").pk, "remarks": "For approval."})
        P(r, kp, "tippani", {"remarks": "Reviewed; proceeding."})
        # 8 approved, waiting for Chalani
        r = self._mk(u["tech_staff"], "Site visit approval - Tansen tower", "OTHER", "NORMAL",
                     "Permission for a two-day site inspection of the Tansen tower.")
        P(r, u["tech_staff"], "submit"); P(r, pp, "verify"); P(r, d, "register")
        P(r, d, "forward", {"to_department": Department.objects.get(code="KP").pk})
        P(r, kp, "tok_aadesh", {"remarks": "Visit approved. Take a safety officer along."})
        P(r, kp, "approve", {"remarks": "Approved as per Tok Aadesh."})
        # 9 dispatched
        r = self._mk(u["rev_staff"], "Revenue report printer toner", "PROCUREMENT", "LOW",
                     "Toner cartridges for the revenue section laser printers.", 18000)
        P(r, u["rev_staff"], "submit"); P(r, u["rajaswa"], "verify"); P(r, d, "register")
        P(r, d, "forward", {"to_department": Department.objects.get(code="KP").pk})
        P(r, kp, "approve"); P(r, c, "process"); P(r, c, "dispatch", {"dispatched_to": "Procurement Unit, Head Office"})
        # 10 completed
        r = self._mk(u["it_staff2"], "Email account for new trainee", "IT_SUPPORT", "LOW",
                     "Create an official mailbox for the incoming trainee.")
        P(r, u["it_staff2"], "submit"); P(r, u["itchief"], "verify"); P(r, d, "register")
        P(r, d, "forward", {"to_department": Department.objects.get(code="KP").pk})
        P(r, kp, "approve"); P(r, c, "dispatch", {"dispatched_to": "IT Sakha"}); P(r, c, "complete")
        # 11 rejected
        r = self._mk(u["rev_staff"], "Purchase of premium office chairs", "PROCUREMENT", "LOW",
                     "Ergonomic premium chairs for the revenue section.", 220000)
        P(r, u["rev_staff"], "submit"); P(r, u["rajaswa"], "verify"); P(r, d, "register")
        P(r, d, "forward", {"to_department": Department.objects.get(code="KP").pk})
        P(r, kp, "reject", {"remarks": "Not within this year's approved budget."})
        # 12 pramukh's own request, straight to Darta
        r = self._mk(u["lekha"], "Audit software licence renewal", "BUDGET", "HIGH",
                     "Annual renewal of the audit software licence.", 95000)
        P(r, u["lekha"], "submit")
