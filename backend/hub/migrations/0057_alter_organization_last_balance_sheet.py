# Generated by Django 4.2.14 on 2024-07-10 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0056_remove_organization_report_2017_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="last_balance_sheet",
            field=models.FileField(
                blank=True,
                default="",
                max_length=300,
                upload_to="",
                verbose_name="Prima pagină a bilanțului contabil pe anul 2023",
            ),
        ),
    ]