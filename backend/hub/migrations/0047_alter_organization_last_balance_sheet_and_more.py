# Generated by Django 4.2.13 on 2024-07-04 12:37

from django.db import migrations, models
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0046_rename_organisation_head_name_organization_organization_head_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="last_balance_sheet",
            field=models.FileField(
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Prima pagină a bilanțului contabil pe anul 2024 depus la Ministerul Finanțelor",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="status",
            field=model_utils.fields.StatusField(
                choices=[
                    ("draft", "Draft"),
                    ("pending", "Pending approval"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                ],
                default="draft",
                max_length=100,
                no_check_for_status=True,
                verbose_name="status",
            ),
        ),
    ]
