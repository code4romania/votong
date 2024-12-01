# Generated by Django 4.2.16 on 2024-12-01 16:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0077_candidate_old_domain"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidatevote",
            name="organization",
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to="hub.organization"),
            preserve_default=False,
        ),
    ]
