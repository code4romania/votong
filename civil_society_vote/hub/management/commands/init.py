from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from hub.models import COMMITTEE_GROUP, FLAG_CHOICES, NGO_GROUP, STAFF_GROUP, SUPPORT_GROUP, EmailTemplate, FeatureFlag

PENDING_ORGS_DIGEST_TEXT = """
Buna ziua,

Un numar de {{ nr_pending_orgs }} organizatii asteapta aprobarea voastra pe platforma VotONG.

Accesati adresa {{ committee_org_list_url }} pentru a vizualiza ultimele aplicatii.

Va multumim!
Echipa VotONG
"""

ORG_APPROVED_TEXT = """
Buna {{ representative }},

Cererea de inscriere a organizatiei "{{ name }}" in platforma VotONG a fost aprobata.

Pentru a va activa contul mergeti la adresa {{ reset_url }}, introduceti adresa de email folosita la inscriere si resetati parola contului.

Va multumim!
Echipa VotONG
"""

ORG_REJECTED_TEXT = """
{{ rejection_message }}
"""


class Command(BaseCommand):
    help = "Add functional data to the system. E.g. user groups, etc."

    def handle(self, *args, **options):
        # NOTE: New initializations added below should be idempotent.
        Group.objects.get_or_create(name=COMMITTEE_GROUP)
        Group.objects.get_or_create(name=STAFF_GROUP)
        Group.objects.get_or_create(name=SUPPORT_GROUP)
        Group.objects.get_or_create(name=NGO_GROUP)

        for flag in [x[0] for x in FLAG_CHOICES]:
            FeatureFlag.objects.get_or_create(flag=flag)

        template, created = EmailTemplate.objects.get_or_create(template="pending_orgs_digest")
        if created:
            template.text_content = PENDING_ORGS_DIGEST_TEXT
            template.save()

        template, created = EmailTemplate.objects.get_or_create(template="org_approved")
        if created:
            template.text_content = ORG_APPROVED_TEXT
            template.save()

        template, created = EmailTemplate.objects.get_or_create(template="org_rejected")
        if created:
            template.text_content = ORG_REJECTED_TEXT
            template.save()

        self.stdout.write(self.style.SUCCESS("Initialization done!"))
