from django.core.management import BaseCommand

from hub.workers.update_organization import start_organization_update_schedule


class Command(BaseCommand):
    """
    Console command for scheduling the organization updater
    """

    help = "Schedule the organization updater to run"

    def handle(self, *args, **options):
        start_organization_update_schedule()

        self.stdout.write(self.style.SUCCESS("Successfully scheduled organization update"))
