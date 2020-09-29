from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from hub.models import COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP


class Command(BaseCommand):
    help = "Add functional data to the system. E.g. user groups, etc."

    def handle(self, *args, **options):
        # NOTE: New initializations added below should be idempotent.
        committee_group, created = Group.objects.get_or_create(name=COMMITTEE_GROUP)
        staff_group, created = Group.objects.get_or_create(name=STAFF_GROUP)
        support_group, created = Group.objects.get_or_create(name=SUPPORT_GROUP)

        self.stdout.write(self.style.SUCCESS("Initialization done!"))
