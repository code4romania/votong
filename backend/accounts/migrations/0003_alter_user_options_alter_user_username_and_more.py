# Generated by Django 4.2.13 on 2024-05-24 06:14

from django.db import migrations, models
import django.db.models.functions.text


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_email_alter_user_first_name_alter_user_id"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={"verbose_name": "Utilizator", "verbose_name_plural": "Users"},
        ),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                editable=False,
                help_text="We do not use this field",
                max_length=150,
                null=True,
                unique=True,
                verbose_name="nume utilizator",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower("email"), name="email_unique"),
        ),
    ]
