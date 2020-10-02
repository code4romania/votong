import os
from shutil import copyfile

from accounts.models import User
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from faker import Faker

from hub.models import COMMITTEE_GROUP, STAFF_GROUP, Candidate, City, Domain, Organization, FeatureFlag

fake = Faker()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG_NUMBER = 60


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting the seeding process"))

        if not User.objects.filter(email="admin@example.test").exists():
            User.objects.create_user("admin", "admin@example.test", "secret", is_staff=True, is_superuser=True)
            self.stdout.write("Created ADMIN user")

        if not User.objects.filter(email="staff@example.test").exists():
            User.objects.create_user("staff", "staff@example.test", "secret")
            self.stdout.write("Created STAFF user")

        if not User.objects.filter(email="ces@example.test").exists():
            User.objects.create_user("ces", "ces@example.test", "secret")
            self.stdout.write("Created CES user")

        committee_group = Group.objects.get(name=COMMITTEE_GROUP)
        staff_group = Group.objects.get(name=STAFF_GROUP)

        staff_user = User.objects.get(username="staff")
        staff_user.groups.add(staff_group)

        ces_user = User.objects.get(username="ces")
        ces_user.groups.add(committee_group)

        self.stdout.write("Done setting up group permissions")

        if not City.objects.count():
            cities = [
                {"city": "Arad", "county": "Arad"},
                {"city": "Timisoara", "county": "Timis"},
                {"city": "Oradea", "county": "Bihor"},
                {"city": "Cluj-Napoca", "county": "Cluj"},
                {"city": "Constanta", "county": "Constanta"},
                {"city": "Iasi", "county": "Iasi"},
                {"city": "Bucuresti", "county": "Bucuresti"},
            ]
            for city_data in cities:
                City.objects.get_or_create(**city_data)

            self.stdout.write("Loaded city data")

        if not Domain.objects.count():
            domains = [
                {"name": "Organizații academice și profesionale", "description": fake.text()},
                {"name": "Organizații cooperatiste și agricole", "description": fake.text()},
                {
                    "name": "Organizații din domeniul social, familia și persoane cu dizabiltăți și pensionari",
                    "description": fake.text(),
                },
                {"name": "Organizații din domeniul sănătății/educației", "description": fake.text()},
                {"name": "Organizații din domeniul mediului", "description": fake.text()},
                {"name": "Organizații pentru Protecția Drepturilor Omului", "description": fake.text()},
            ]
            for domain in domains:
                Domain.objects.get_or_create(**domain)

            self.stdout.write("Loaded domain data")

        if not Organization.objects.count():
            if not (os.path.isdir(os.path.join(BASE_DIR, "../../", "mediafiles"))):
                os.mkdir(os.path.join(BASE_DIR, "../../", "mediafiles"))

            if not (os.path.exists(os.path.join(BASE_DIR, "../../", "mediafiles"))):
                os.mkdir(os.path.join(BASE_DIR, "../../", "mediafiles"))

            copyfile(
                os.path.join(BASE_DIR, "../../", "static/images/logo-demo.png"),
                os.path.join(BASE_DIR, "../../", "mediafiles/logo-demo.png"),
            )
            copyfile(
                os.path.join(BASE_DIR, "../../", "static/images/photo-placeholder.gif"),
                os.path.join(BASE_DIR, "../../", "mediafiles/photo-placeholder.gif"),
            )
            copyfile(
                os.path.join(BASE_DIR, "../../", "static/data/test.pdf"),
                os.path.join(BASE_DIR, "../../", "mediafiles/test.pdf"),
            )

            for i in range(ORG_NUMBER):
                city = City.objects.order_by("?").first()
                domain = Domain.objects.order_by("?").first()
                status = ["pending", "accepted", "rejected"][i % 3]

                org = Organization.objects.create(
                    name=fake.company(),
                    description=fake.text(),
                    email=fake.safe_email(),
                    phone=fake.phone_number(),
                    address=fake.address(),
                    reg_com_number=fake.ssn(),
                    purpose_initial=fake.sentence(),
                    purpose_current=fake.sentence(),
                    founders=fake.name(),
                    legal_representative_name=fake.name(),
                    board_council=fake.name(),
                    city=city,
                    county=city.county,
                    status=status,
                )

                org.logo.name = "logo-demo.png"
                org.last_balance_sheet.name = "test.pdf"
                org.statute.name = "test.pdf"
                org.letter.name = "test.pdf"
                org.save()

                if status == "rejected":
                    self.stdout.write(f"Created organization {org}")
                elif status == "accepted":
                    candidate = Candidate.objects.create(
                        org=org,
                        name=org.legal_representative_name,
                        description=fake.text(),
                        role=fake.job(),
                        experience=fake.text(),
                        studies=fake.text(),
                        email=fake.safe_email(),
                        phone=fake.phone_number(),
                        domain=domain,
                    )

                    candidate.photo.name = "photo-placeholder.gif"
                    candidate.mandate.name = "test.pdf"
                    candidate.letter.name = "test.pdf"
                    candidate.statement.name = "test.pdf"
                    candidate.cv.name = "test.pdf"
                    candidate.legal_record.name = "test.pdf"
                    candidate.save()

                    self.stdout.write(f"Created organization {org} and candidate {candidate.name}")

        self.stdout.write("Loaded organizations data")

        flags = [
            "enable_org_registration",
            "enable_org_approval",
            "enable_org_voting",
            "enable_candidate_registration",
            "enable_candidate_voting"
        ]

        for flag in flags:
            feature_flag_obj, _ = FeatureFlag.objects.get_or_create(flag=flag)
            feature_flag_obj.is_enabled = True
            feature_flag_obj.save()
            self.stdout.write(self.style.SUCCESS(f"Enabled {flag}"))    


        self.stdout.write(self.style.SUCCESS("Seeding finished"))
