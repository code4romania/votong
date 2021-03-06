# Generated by Django 2.2.16 on 2020-10-06 08:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0022_merge_20201006_0815"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="main_objectives",
            field=models.TextField(
                default="",
                help_text="What are your main goals if you get a seat on the Economic and Social Committee?",
                max_length=1000,
                verbose_name="Main Objectives",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="candidate",
            name="main_points",
            field=models.TextField(
                default="",
                help_text="What are the most important points that should be on the agenda of the field for which you are applying?",
                max_length=1000,
                verbose_name="Main Points",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="candidate",
            name="relevant_moments",
            field=models.TextField(
                default="",
                help_text="What are the most relevant moments in your experience that recommend you to take a place in the Economic and Social Committee?",
                max_length=1000,
                verbose_name="Relevant Moments",
            ),
            preserve_default=False,
        ),
    ]
