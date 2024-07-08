# Generated by Django 4.2.13 on 2024-07-05 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0049_delete_emailtemplate_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="organization",
            name="logo_url",
        ),
        migrations.AddField(
            model_name="organization",
            name="filename_cache",
            field=models.JSONField(default=dict, editable=False, verbose_name="Filename cache"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="last_balance_sheet",
            field=models.FileField(
                max_length=300, null=True, upload_to="", verbose_name="First page of last balance sheet for 2024"
            ),
        ),
    ]
