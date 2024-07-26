# Generated by Django 4.2.14 on 2024-07-23 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0058_alter_blogpost_content"),
    ]

    operations = [
        migrations.AlterField(
            model_name="featureflag",
            name="flag",
            field=models.CharField(
                choices=[
                    ("enable_org_registration", "Enable organization registration"),
                    ("enable_org_approval", "Enable organization approvals"),
                    ("enable_org_voting", "Enable organization voting"),
                    ("enable_candidate_registration", "Enable candidate registration"),
                    ("enable_candidate_supporting", "Enable candidate supporting"),
                    ("enable_candidate_voting", "Enable candidate voting"),
                    ("enable_results_display", "Enable the display of results"),
                    ("single_domain_round", "Voting round with just one domain (some restrictions will apply)"),
                    (
                        "global_support_round",
                        "Enable global support (the support of at least 10 organizations is required)",
                    ),
                ],
                max_length=254,
                unique=True,
                verbose_name="Flag",
            ),
        ),
    ]