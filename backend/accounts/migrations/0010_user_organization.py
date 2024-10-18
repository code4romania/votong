# Generated by Django 4.2.16 on 2024-10-18 08:16

import django.db.models.deletion
from django.db import migrations, models


def reverse_user_organization_relationship(apps, _):
    UserModel = apps.get_model("accounts", "User")

    for user in UserModel.objects.all():
        if user_org := user.orgs.first():
            user.organization = user_org
            user.save()


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0066_organization_voting_domain_alter_candidate_domain_and_more"),
        ("accounts", "0009_alter_user_options_alter_user_username"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="hub.organization",
            ),
        ),
        migrations.RunPython(
            code=reverse_user_organization_relationship,
            reverse_code=migrations.RunPython.noop,
        ),
    ]