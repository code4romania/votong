# Generated by Django 4.2.13 on 2024-07-03 04:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0043_organization_logo_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidate",
            name="domain",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="candidates",
                to="hub.domain",
                verbose_name="Domain",
            ),
        ),
    ]