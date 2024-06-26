# Generated by Django 4.2.13 on 2024-06-28 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0041_alter_blogpost_id_alter_candidate_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="ngohub_org_id",
            field=models.PositiveBigIntegerField(
                db_index=True, default=0, verbose_name="NGO Hub linked organisation ID"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="report_2021",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2021",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="report_2022",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2022",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="report_2023",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2023",
            ),
        ),
    ]
