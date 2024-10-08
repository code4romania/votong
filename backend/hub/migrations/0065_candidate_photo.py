# Generated by Django 4.2.15 on 2024-08-20 13:46

from django.db import migrations, models
import hub.models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0064_alter_featureflag_flag"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="photo",
            field=models.ImageField(
                blank=True,
                default="",
                max_length=300,
                storage=hub.models.select_public_storage,
                upload_to="",
                verbose_name="Candidate photo",
            ),
        ),
    ]
