from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from hub.models import ORG_VOTERS_GROUP


class Command(BaseCommand):
    help = "Add functional data to the system. E.g. user groups, etc."

    def handle(self, *args, **options):
        # NOTE: New initializations added below should be idempotent.
        org_voters_group, created = Group.objects.get_or_create(name=ORG_VOTERS_GROUP)
        self.stdout.write(self.style.SUCCESS("Initialization done!"))
