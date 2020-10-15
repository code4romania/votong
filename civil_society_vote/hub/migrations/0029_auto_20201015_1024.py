# Generated by Django 2.2.16 on 2020-10-15 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0028_auto_20201009_1039"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="accept_terms_and_conditions",
            field=models.BooleanField(default=False, verbose_name="Accepted Terms and Conditions"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="politic_members",
            field=models.BooleanField(default=False, verbose_name="Has political party members"),
        ),
    ]