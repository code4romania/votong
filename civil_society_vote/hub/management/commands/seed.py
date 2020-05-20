import random

import requests
from faker import Faker

from django.contrib.auth.models import User, Group, Permission
from django.core.management.base import BaseCommand

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


def random_logo():
    try:
        image = requests.get("https://source.unsplash.com/random", allow_redirects=False)
        return image.headers["Location"]
    except Exception:
        return "https://source.unsplash.com/random"


NGOS = [
    {
        "name": "Habitat for Humanity",
        "email": "habitat@habitat.ro",
        "phone": "+40722644394",
        "address": "Str. Naum Râmniceanu, nr. 45 A, et.1, ap. 3, sector 1, Bucuresti 011616",
        "city": "Bucuresti",
        "county": "Bucuresti",
        "domain": 1,
        "logo": "http://www.habitat.ro/wp-content/uploads/2014/11/logo.png",
    },
    {
        "name": "Crucea Roșie",
        "email": "matei@crucearosie.ro",
        "phone": "+40213176006",
        "address": "Strada Biserica Amzei, nr. 29, Sector 1, Bucuresti",
        "city": "Bucuresti",
        "county": "Bucuresti",
        "domain": 1,
        "logo": "https://crucearosie.ro/themes/redcross/images/emblema_crr_desktop.png",
    },
    {
        "name": "MKBT: Make Better",
        "email": "contact@mkbt.ro",
        "phone": "+40213176006",
        "address": "Str. Popa Petre, Nr. 23, Sector 2, 020802, Bucharest, Romania.",
        "city": "Bucuresti",
        "county": "Bucuresti",
        "domain": 1,
        "logo": "http://mkbt.ro/wp-content/uploads/2015/08/MKBT-logo-alb.png",
    },
] + [
    {
        "name": fake.name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "address": fake.address(),
        "city": ["Arad", "Timisoara", "Oradea", "Cluj-Napoca", "Bucuresti"][i],
        "county": ["Arad", "Timis", "Bihor", "Cluj", "Bucuresti"][i],
        "logo": random_logo(),
        "domain": 1,
    }
    for i in range(5)
]


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_user("admin", "admin@admin.com", "admin", is_staff=True, is_superuser=True)

        if not User.objects.filter(username="user").exists():
            User.objects.create_user("user", "user@user.com", "user", is_staff=True)

        if not User.objects.filter(username="dsu").exists():
            User.objects.create_user("dsu", "user@user.com", "dsu", is_staff=True)

        if not User.objects.filter(username="ffc").exists():
            User.objects.create_user("ffc", "user@user.com", "ffc", is_staff=True)

        admin_user = User.objects.get(username="admin")
        ngo_user = User.objects.get(username="user")
        dsu_user = User.objects.get(username="dsu")
        ffc_user = User.objects.get(username="ffc")

        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
        ngo_group, _ = Group.objects.get_or_create(name=NGO_GROUP_NAME)
        dsu_group, _ = Group.objects.get_or_create(name=CES_GROUP_NAME)
        ffc_group, _ = Group.objects.get_or_create(name=SGG_GROUP_NAME)

        # models.NamedCredentials: ['add', 'change', 'delete', 'view'],
        GROUPS_PERMISSIONS = {
            NGO_GROUP_NAME: {Organization: ["change", "view"]},
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
                        self.stdout.write("Adding " + codename + " to group " + group.__str__())
                    except Permission.DoesNotExist:
                        self.stdout.write(codename + " not found")

        admin_user.groups.add(admin_group)
        admin_user.save()

        ngo_user.groups.add(ngo_group)
        ngo_user.save()

        dsu_user.groups.add(dsu_group)
        dsu_user.save()

        ffc_user.groups.add(ffc_group)
        ffc_user.save()

        Organization.objects.filter(
            pk__in=Organization.objects.exclude(name__in=["Code4Romania", "Crucea Roșie"])
            .order_by("created")
            .values_list("pk")[100:]
        ).delete()

        cities = [
            {"city": "Arad", "county": "Arad"},
            {"city": "Timisoara", "county": "Timis"},
            {"city": "Oradea", "county": "Bihor"},
            {"city": "Cluj-Napoca", "county": "Cluj"},
            {"city": "Bucuresti", "county": "Bucuresti"},
        ]
        for city_data in cities:
            City.objects.get_or_create(**city_data)

        for details in NGOS:
            details["city"] = City.objects.get(city=details["city"], county=details["county"])
            details["county"] = details["county"]

            ngo, _ = Organization.objects.get_or_create(**details)

            owner = random.choice([ngo_user, admin_user, None])
            if owner:
                ngo.user = owner
                ngo.save()
