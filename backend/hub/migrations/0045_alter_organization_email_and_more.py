# Generated by Django 4.2.13 on 2024-07-03 05:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0044_alter_candidate_domain"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="email",
            field=models.EmailField(max_length=254, verbose_name="Organization Email"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="ngohub_org_id",
            field=models.PositiveBigIntegerField(
                db_index=True, default=0, verbose_name="NGO Hub linked organization ID"
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="organisation_head_name",
            field=models.CharField(default="", max_length=254, verbose_name="Organization Head Name"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="phone",
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name="Organization Phone"),
        ),
    ]
