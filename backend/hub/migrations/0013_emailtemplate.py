# Generated by Django 2.2.16 on 2020-10-02 08:15

import tinymce.models
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0012_auto_20201002_0730"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailTemplate",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                (
                    "template",
                    models.CharField(
                        choices=[
                            ("pending_orgs_digest", "Pending organizations digest email"),
                            ("org_approved", "You organizations was approved"),
                            ("org_rejected", "You organizations was rejected"),
                        ],
                        max_length=254,
                        unique=True,
                        verbose_name="Template",
                    ),
                ),
                ("text_content", models.TextField(verbose_name="Text content")),
                ("html_content", tinymce.models.HTMLField(verbose_name="HTML content", blank=True)),
            ],
            options={
                "verbose_name": "Email template",
                "verbose_name_plural": "Email templates",
            },
        ),
    ]
