from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm

from hub.models import COMMITTEE_GROUP, FLAG_CHOICES, FeatureFlag, NGO_GROUP, STAFF_GROUP, SUPPORT_GROUP


class Command(BaseCommand):
    help = "Add functional data to the system. E.g. user groups, etc."

    def handle(self, *args, **options):
        # NOTE: New initializations added below should be idempotent.

        committee_group = Group.objects.get_or_create(name=COMMITTEE_GROUP)[0]
        assign_perm("hub.approve_candidate", committee_group)
        assign_perm("hub.view_data_candidate", committee_group)

        staff_group = Group.objects.get_or_create(name=STAFF_GROUP)[0]
        assign_perm("hub.view_data_candidate", staff_group)

        support_group = Group.objects.get_or_create(name=SUPPORT_GROUP)[0]
        assign_perm("hub.view_data_candidate", support_group)

        ngo_group = Group.objects.get_or_create(name=NGO_GROUP)[0]
        assign_perm("hub.support_candidate", ngo_group)
        assign_perm("hub.vote_candidate", ngo_group)

        for flag in [x[0] for x in FLAG_CHOICES]:
            FeatureFlag.objects.get_or_create(flag=flag)

        self.stdout.write(self.style.SUCCESS("Initialization done!"))
