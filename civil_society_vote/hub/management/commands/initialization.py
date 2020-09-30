from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from hub.models import COMMITTEE_GROUP, NGO_GROUP, STAFF_GROUP, SUPPORT_GROUP, FeatureFlag


class Command(BaseCommand):
    help = "Add functional data to the system. E.g. user groups, etc."

    def handle(self, *args, **options):
        # NOTE: New initializations added below should be idempotent.
        Group.objects.get_or_create(name=COMMITTEE_GROUP)
        Group.objects.get_or_create(name=STAFF_GROUP)
        Group.objects.get_or_create(name=SUPPORT_GROUP)
        Group.objects.get_or_create(name=NGO_GROUP)

        FeatureFlag.objects.get_or_create(flag="enable_org_registration")
        FeatureFlag.objects.get_or_create(flag="enable_org_approval")
        FeatureFlag.objects.get_or_create(flag="enable_candidate_registration")
        FeatureFlag.objects.get_or_create(flag="enable_org_voting")
        FeatureFlag.objects.get_or_create(flag="enable_candidate_voting")

        self.stdout.write(self.style.SUCCESS("Initialization done!"))
