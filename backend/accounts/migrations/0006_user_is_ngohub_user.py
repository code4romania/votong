# Generated by Django 4.2.13 on 2024-07-03 03:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_alter_user_options_alter_user_username"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_ngohub_user",
            field=models.BooleanField(default=False),
        ),
    ]