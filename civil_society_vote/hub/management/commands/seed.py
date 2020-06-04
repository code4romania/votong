from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from faker import Faker

from hub.models import ORG_VOTERS_GROUP, Candidate, City, Domain, Organization

fake = Faker()

ORG_NUMBER = 60


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Starting the seeding process"))

        if not User.objects.filter(username="admin").exists():
            User.objects.create_user("admin", "admin@example.test", "secret", is_staff=True, is_superuser=True)
            self.stdout.write(self.style.SUCCESS("Created ADMIN user"))

        if not User.objects.filter(username="ces").exists():
            User.objects.create_user("ces", "ces@example.test", "secret")
            self.stdout.write(self.style.SUCCESS("Created CES user"))

        if not User.objects.filter(username="sgg").exists():
            User.objects.create_user("sgg", "sgg@example.test", "secret")
            self.stdout.write(self.style.SUCCESS("Created SGG user"))

        org_voters_group = Group.objects.get(name=ORG_VOTERS_GROUP)

        ces_user = User.objects.get(username="ces")
        ces_user.groups.add(org_voters_group)

        sgg_user = User.objects.get(username="sgg")
        sgg_user.groups.add(org_voters_group)

        self.stdout.write(self.style.SUCCESS("Done setting up group permissions"))

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

            self.stdout.write(self.style.SUCCESS("Loaded city data"))

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

            self.stdout.write(self.style.SUCCESS("Loaded domain data"))

        if not Organization.objects.count():
            count_org_voters = 0

            for i in range(ORG_NUMBER):
                city = City.objects.order_by("?").first()
                domain = Domain.objects.order_by("?").first()

                org = Organization.objects.create(
                    name=fake.company(),
                    email=fake.safe_email(),
                    phone=fake.phone_number(),
                    address=fake.address(),
                    domain=domain,
                    reg_com_number=fake.ssn(),
                    purpose_initial=fake.sentence(),
                    purpose_current=fake.sentence(),
                    founders=fake.name(),
                    representative=fake.name(),
                    board_council=fake.name(),
                    city=city,
                    county=city.county,
                )

                status = ["pending", "accepted", "rejected"][i % 3]

                if status == "rejected":
                    org.reject(request=None)
                    self.stdout.write(self.style.SUCCESS(f"Created organization {org}"))
                elif status == "accepted":
                    org.accept(request=None)

                    # we add a few org users to the voting group
                    if count_org_voters < 3:
                        org.user.groups.add(org_voters_group)
                        count_org_voters += 1

                    candidate = Candidate.objects.create(
                        org=org,
                        name=org.representative,
                        role=fake.job(),
                        experience=fake.text(),
                        studies=fake.text(),
                        representative=True,
                        email=fake.safe_email(),
                        phone=fake.phone_number(),
                        domain=org.domain,
                    )

                    self.stdout.write(self.style.SUCCESS(f"Created organization {org} and candidate {candidate.name}"))

        self.stdout.write(self.style.SUCCESS("Loaded organizations data"))

        self.stdout.write(self.style.NOTICE("Seeding finished"))
