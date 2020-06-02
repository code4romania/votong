from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from faker import Faker

from hub.models import (
    ADMIN_GROUP_NAME,
    CES_GROUP_NAME,
    NGO_GROUP_NAME,
    SGG_GROUP_NAME,
    Candidate,
    City,
    Domain,
    Organization,
    OrganizationVote,
)

fake = Faker()

ORG_NUMBER = 30


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

        admin_user = User.objects.get(username="admin")
        ces_user = User.objects.get(username="ces")
        sgg_user = User.objects.get(username="sgg")

        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
        ngo_group, _ = Group.objects.get_or_create(name=NGO_GROUP_NAME)
        ces_group, _ = Group.objects.get_or_create(name=CES_GROUP_NAME)
        sgg_group, _ = Group.objects.get_or_create(name=SGG_GROUP_NAME)

        self.stdout.write(self.style.SUCCESS("Loaded groups data"))

        # models.NamedCredentials: ['add', 'change', 'delete', 'view'],
        GROUPS_PERMISSIONS = {
            NGO_GROUP_NAME: {Organization: ["view", "change"]},
            CES_GROUP_NAME: {Organization: ["view", "change"], OrganizationVote: ["view", "change"],},
            SGG_GROUP_NAME: {Organization: ["view", "change"], OrganizationVote: ["view", "change"],},
        }

        for group_name in GROUPS_PERMISSIONS:

            # Get or create group
            group, created = Group.objects.get_or_create(name=group_name)

            # Loop models in group
            for model_cls in GROUPS_PERMISSIONS[group_name]:

                # Loop permissions in group/model
                for perm_index, perm_name in enumerate(GROUPS_PERMISSIONS[group_name][model_cls]):

                    # Generate permission name as Django would generate it
                    codename = perm_name + "_" + model_cls._meta.model_name

                    try:
                        # Find permission object and add to group
                        perm = Permission.objects.get(codename=codename)
                        group.permissions.add(perm)
                        self.stdout.write(self.style.SUCCESS("Adding " + codename + " to group " + group.name))
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.ERROR(codename + " not found"))

        admin_user.groups.add(admin_group)
        admin_user.save()

        ces_user.groups.add(ces_group)
        ces_user.save()

        sgg_user.groups.add(sgg_group)
        sgg_user.save()

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
                {"name": "Organizații academice și profesionale"},
                {"name": "Organizații cooperatiste și agricole"},
                {"name": "Organizații din domeniul social, familia și persoane cu dizabiltăți și pensionari"},
                {"name": "Organizații din domeniul sănătății/educației"},
                {"name": "Organizații din domeniul mediului"},
                {"name": "Organizații pentru Protecția Drepturilor Omului"},
            ]
            for domain in domains:
                Domain.objects.get_or_create(**domain)

            self.stdout.write(self.style.SUCCESS("Loaded domain data"))

        if not Organization.objects.count():
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
                    status=["pending", "accepted", "rejected"][i % 3],
                    logo="/static/images/logo-demo.png",
                    last_balance_sheet="/static/data/test.pdf",
                    statute="/static/data/test.pdf",
                    letter="/static/data/test.pdf",
                )

                owner = User.objects.create_user(
                    fake.user_name(),
                    email=org.email,
                    password="secret",
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                )
                owner.groups.add(ngo_group)
                owner.save()

                org.user = owner
                org.save()

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
                    photo="/static/images/photo-placeholder.gif",
                    mandate="/static/data/test.pdf",
                    letter="/static/data/test.pdf",
                    statement="/static/data/test.pdf",
                    cv="/static/data/test.pdf",
                    legal_record="/static/data/test.pdf",
                )

                self.stdout.write(self.style.SUCCESS(f"Created organization {org} with candidate {candidate.name}"))

        self.stdout.write(self.style.SUCCESS("Loaded organizations data"))

        self.stdout.write(self.style.NOTICE("Seeding finished"))
