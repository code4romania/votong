import json
from typing import Dict, List

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm

from accounts.models import COMMITTEE_GROUP, NGO_GROUP, STAFF_GROUP, SUPPORT_GROUP
from hub.models import City, FLAG_CHOICES, FeatureFlag


class Command(BaseCommand):
    help = "Add functional data to the system in an idempotent way (i.e. user groups, cities, feature flags, etc.)"

    def handle(self, *args, **options):
        # IMPORTANT: Initializations should be idempotent.
        self.stdout.write(self.style.SUCCESS("Initializing..."))

        self._initialize_groups_permissions()
        self._initialize_feature_flags()
        self._import_cities()

        self.stdout.write(self.style.SUCCESS("Initialization done!"))

    def _initialize_groups_permissions(self):
        self.stdout.write(self.style.NOTICE("Initializing groups and permissions..."))

        committee_group: Group = Group.objects.get_or_create(name=COMMITTEE_GROUP)[0]
        assign_perm("hub.approve_candidate", committee_group)
        assign_perm("hub.view_data_candidate", committee_group)

        staff_group: Group = Group.objects.get_or_create(name=STAFF_GROUP)[0]
        assign_perm("hub.view_data_candidate", staff_group)

        support_group: Group = Group.objects.get_or_create(name=SUPPORT_GROUP)[0]
        assign_perm("hub.view_data_candidate", support_group)

        ngo_group: Group = Group.objects.get_or_create(name=NGO_GROUP)[0]
        assign_perm("hub.support_candidate", ngo_group)
        assign_perm("hub.vote_candidate", ngo_group)
        assign_perm("hub.change_organization", ngo_group)

    def _initialize_feature_flags(self):
        self.stdout.write(self.style.NOTICE("Initializing feature flags..."))

        for flag in [x[0] for x in FLAG_CHOICES]:
            FeatureFlag.objects.get_or_create(flag=flag)

    def _import_cities(self):
        self.stdout.write(self.style.NOTICE("Importing cities..."))

        fixture_path: str = f"{settings.BASE_DIR}/hub/fixtures/cities.json"
        cities_data: Dict = json.load(open(fixture_path))

        self.stdout.write(self.style.NOTICE(f"Cities in the database: {City.objects.count()} before import"))

        batch_size: int = 1000
        cities_to_create: List[City] = [City(**city_data) for city_data in cities_data]
        for start in range(0, len(cities_to_create), batch_size):
            end: int = start + batch_size
            City.objects.bulk_create(cities_to_create[start:end], ignore_conflicts=True)

        self.stdout.write(self.style.NOTICE(f"Cities in the database: {City.objects.count()} after import"))
