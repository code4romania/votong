# Generated by Django 4.2.16 on 2024-12-01 13:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0076_alter_candidate_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="old_domain",
            field=models.ForeignKey(
                blank=True,
                help_text="The domain in which the candidate is running.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="candidates_old",
                to="hub.domain",
                verbose_name="Old Domain",
            ),
        ),
    ]
