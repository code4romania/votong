# Generated by Django 4.2.14 on 2024-07-22 21:12

from django.db import migrations
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0057_alter_organization_last_balance_sheet"),
    ]

    operations = [
        migrations.AlterField(
            model_name="blogpost",
            name="content",
            field=tinymce.models.HTMLField(verbose_name="Content"),
        ),
    ]
