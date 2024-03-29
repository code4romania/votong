# Generated by Django 2.2.24 on 2021-11-09 19:07

import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0037_blogpost"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="candidate",
            name="cv",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="description",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="email",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="experience",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="legal_records",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="letter",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="main_objectives",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="main_points",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="mandate",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="phone",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="photo",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="relevant_moments",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="studies",
        ),
        migrations.RemoveField(
            model_name="candidate",
            name="tax_records",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="fiscal_certificate",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="politic_members",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="statement",
        ),
        migrations.AddField(
            model_name="organization",
            name="fiscal_certificate_anaf",
            field=models.FileField(
                blank=True,
                help_text="Certificat fiscal emis de ANAF",
                max_length=300,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(),
                upload_to="",
                verbose_name="Fiscal certificate ANAF",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="fiscal_certificate_local",
            field=models.FileField(
                blank=True,
                help_text="Certificat fiscal emis de Direcția de Impozite și Taxe Locale",
                max_length=300,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(),
                upload_to="",
                verbose_name="Fiscal certificate local",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="report_2020",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi materiale pentru îndeplinirea mandatului de reprezentare a organizaţiilor votante în CES.",
                max_length=300,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(),
                upload_to="",
                verbose_name="Yearly report 2020",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="statement_discrimination",
            field=models.FileField(
                blank=True,
                help_text="Declarație pe proprie răspundere prin care declară că nu realizează activități sau susține cauze de natură politică sau care discriminează pe considerente legate de etnie, rasă, sex, orientare sexuală, religie, capacități fizice sau psihice sau de apartenența la una sau mai multe categorii sociale sau economice.",
                max_length=300,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(),
                upload_to="",
                verbose_name="Non-discrimination statement",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="statement_political",
            field=models.FileField(
                blank=True,
                help_text="Declarație pe propria răspundere prin care declar că ONG-ul nu are între membrii conducerii organizației (Președinte sau Consiliul Director) membri ai conducerii unui partid politic sau persoane care au fost alese într-o funcție publică.",
                max_length=300,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(),
                upload_to="",
                verbose_name="Non-political statement",
            ),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="name",
            field=models.CharField(
                help_text="Numele persoanei care va reprezenta organizatia in Comisia Electorală în cazul unui răspuns favorabil. Persoana desemnată trebuie să fie angajat în cadrul organizației și parte din structurile de conducere ale acesteia (membru în Consiliul Director, Director Executiv etc)",
                max_length=254,
                verbose_name="Representative name",
            ),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="role",
            field=models.CharField(
                help_text="Funcția în organizației a persoanei desemnate.",
                max_length=254,
                verbose_name="Representative role in organization",
            ),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="statement",
            field=models.FileField(
                help_text="Declarație pe propria răspundere a reprezentantului desemnat prin care declară că nu este membru al conducerii unui partid politic, nu a fost ales într-o funcție publică și nu este demnitar al statului român.",
                max_length=300,
                null=True,
                storage=django.core.files.storage.FileSystemStorage(),
                upload_to="",
                verbose_name="Representative statement",
            ),
        ),
    ]
