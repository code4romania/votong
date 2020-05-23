from django.contrib.auth.models import User, Group, Permission
from django.core.management.base import BaseCommand

from faker import Faker

from hub.models import (
    City,
    Organization,
    OrganizationVote,
    ADMIN_GROUP_NAME,
    NGO_GROUP_NAME,
    CES_GROUP_NAME,
    SGG_GROUP_NAME,
)

fake = Faker()

ORGS = [
    {
        "name": fake.company(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "address": fake.address(),
        "domain": ((i % 6) + 1),
        "reg_com_number": fake.ssn(),
        "purpose_initial": fake.sentence(),
        "purpose_current": fake.sentence(),
        "founders": fake.name(),
        "representative": fake.name(),
        "board_council": fake.name(),
        "city": ["Arad", "Timisoara", "Oradea", "Cluj-Napoca", "Bucuresti"][i % 5],
        "county": ["Arad", "Timis", "Bihor", "Cluj", "Bucuresti"][i % 5],
        "status": ["pending", "accepted", "rejected"][i % 3],
    }
    for i in range(30)
]


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

        cities = [
            {"city": "Arad", "county": "Arad"},
            {"city": "Timisoara", "county": "Timis"},
            {"city": "Oradea", "county": "Bihor"},
            {"city": "Cluj-Napoca", "county": "Cluj"},
            {"city": "Bucuresti", "county": "Bucuresti"},
        ]
        for city_data in cities:
            City.objects.get_or_create(**city_data)

        self.stdout.write(self.style.SUCCESS("Loaded city data"))

        for details in ORGS:
            details["city"] = City.objects.get(city=details["city"], county=details["county"])
            details["county"] = details["county"]

            org, _ = Organization.objects.get_or_create(**details)

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

            self.stdout.write(self.style.SUCCESS(f"Created organization: {org}"))

        self.stdout.write(self.style.SUCCESS("Loaded organizations data"))

        self.stdout.write(self.style.NOTICE("Seeding finished"))
