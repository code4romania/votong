import random

import requests
from faker import Faker

from django.contrib.auth.models import User, Group, Permission
from django.core.management.base import BaseCommand

from hub.models import (
    NGO,
    PendingRegisterNGORequest,
    RegisterNGORequest,
    RegisterNGORequestVote,
    ADMIN_GROUP_NAME,
    NGO_GROUP_NAME,
    DSU_GROUP_NAME,
    FFC_GROUP_NAME,
)

fake = Faker()


def random_logo():
    try:
        image = requests.get(
            "https://source.unsplash.com/random", allow_redirects=False
        )
        return image.headers["Location"]
    except Exception:
        return "https://source.unsplash.com/random"


NGOS = (
    [
        {
            "name": "Habitat for Humanity",
            "email": "habitat@habitat.ro",
            "description": """
        O locuință decentă poate rupe cercul sărăciei. Credem cu tărie în acest lucru din 1976, de când lucrăm pentru
        viziunea noastră: o lume în care toți oamenii au posibilitatea să locuiască decent. Cu sprijinul nostru,
        peste 6 milioane de oameni din peste 70 de țări au un loc mai bun în care să trăiască, o casă nouă sau una
        complet renovată.Suntem o asociație creștină, non-profit, ce lucrăm alături de oameni de pretutindeni,
        din toate păturile sociale, rasele, religiile și naționalitățile pentru a elimina locuirea precară.
        """,
            "phone": "+40722644394",
            "address": "Str. Naum Râmniceanu, nr. 45 A, et.1, ap. 3, sector 1, Bucureşti 011616",
            "city": "Bucureşti",
            "county": "Sector 1",
            "logo": "http://www.habitat.ro/wp-content/uploads/2014/11/logo.png",
        },
        {
            "name": "Crucea Roșie",
            "email": "matei@crucearosie.ro",
            "description": """
         Crucea Rosie Romana asista persoanele vulnerabile in situatii de dezastre si de criza. Prin programele si
         activitatile sale in beneficiul societatii, contribuie la prevenirea si alinarea suferintei sub toate formele,
          protejeaza sanatatea si viata, promoveaza respectul fata de demnitatea umana, fara nicio discriminare bazata
          pe nationalitate, rasa, sex, religie, varsta, apartenenta sociala sau politica.
        """,
            "phone": "+40213176006",
            "address": "Strada Biserica Amzei, nr. 29, Sector 1, Bucuresti",
            "city": "Bucuresti",
            "county": "Sector 1",
            "logo": "https://crucearosie.ro/themes/redcross/images/emblema_crr_desktop.png",
        },
        {
            "name": "MKBT: Make Better",
            "email": "contact@mkbt.ro",
            "description": """
        MKBT: Make Better has been working for urban development and regeneration in Romania since April 2014.
        That is to say that we are drafting, validating and coordinating processes for local development and urban
        regeneration in order to help as many cities become their best possible version and the best home for their inhabitants.
        As a local development advisor, we assist both public and private entities.
        We substantiate our work on a thorough understanding of local needs and specificities of the communities we
        work with. We acknowledge, at the same time, the global inter-connectivity of local challenges. Our proposed
        solutions are therefore grounded in international best practice, while at the same time capitalizing – in a
         sustainable and harmonious manner – on local know how and resources.
        """,
            "phone": "+40213176006",
            "address": "Str. Popa Petre, Nr. 23, Sector 2, 020802, Bucharest, Romania.",
            "city": "Bucuresti",
            "county": "Sector 2",
            "logo": "http://mkbt.ro/wp-content/uploads/2015/08/MKBT-logo-alb.png",
        },
    ]
    + [
        {
            "name": fake.name(),
            "email": fake.email(),
            "description": fake.text(),
            "phone": fake.phone_number(),
            "address": fake.address(),
            "city": random.choice(["Arad", "Timisoara", "Oradea", "Cluj", "Bucuresti"]),
            "county": random.choice(
                ["ARAD", "TIMIS", "BIHOR", "CLUJ", "SECTOR 1", "SECTOR 2"]
            ),
            "logo": random_logo(),
        }
        for _ in range(2)
    ]
)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_user(
                "admin", "admin@admin.com", "admin", is_staff=True, is_superuser=True
            )

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
        dsu_group, _ = Group.objects.get_or_create(name=DSU_GROUP_NAME)
        ffc_group, _ = Group.objects.get_or_create(name=FFC_GROUP_NAME)

        # models.NamedCredentials: ['add', 'change', 'delete', 'view'],
        GROUPS_PERMISSIONS = {
            NGO_GROUP_NAME: {NGO: ["change", "view"],},
            DSU_GROUP_NAME: {
                PendingRegisterNGORequest: ["view", "change"],
                RegisterNGORequest: ["view"],
                RegisterNGORequestVote: ["view", "change"],
            },
            FFC_GROUP_NAME: {
                PendingRegisterNGORequest: ["view", "change"],
                RegisterNGORequest: ["view"],
                RegisterNGORequestVote: ["view", "change"],
            },
        }

        for group_name in GROUPS_PERMISSIONS:

            # Get or create group
            group, created = Group.objects.get_or_create(name=group_name)

            # Loop models in group
            for model_cls in GROUPS_PERMISSIONS[group_name]:

                # Loop permissions in group/model
                for perm_index, perm_name in enumerate(
                    GROUPS_PERMISSIONS[group_name][model_cls]
                ):

                    # Generate permission name as Django would generate it
                    codename = perm_name + "_" + model_cls._meta.model_name

                    try:
                        # Find permission object and add to group
                        perm = Permission.objects.get(codename=codename)
                        group.permissions.add(perm)
                        self.stdout.write(
                            "Adding " + codename + " to group " + group.__str__()
                        )
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

        NGO.objects.filter(
            pk__in=NGO.objects.exclude(name__in=["Code4Romania", "Crucea Roșie"])
            .order_by("created")
            .values_list("pk")[100:]
        ).delete()

        for details in NGOS:
            ngo, _ = NGO.objects.get_or_create(**details)

            owner = random.choice([ngo_user, admin_user, None])
            if owner:
                ngo.users.add(owner)
                ngo.save()
