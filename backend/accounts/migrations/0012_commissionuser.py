# Generated by Django 4.2.16 on 2024-11-23 13:58

import django.contrib.auth.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_groupproxy_user_created_user_modified_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommissionUser",
            fields=[],
            options={
                "verbose_name": "Utilizator Comisie Electorală",
                "verbose_name_plural": "Utilizatori Comisie Electorală",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("accounts.user",),
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
