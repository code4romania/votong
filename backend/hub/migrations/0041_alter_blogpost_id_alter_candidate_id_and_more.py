# Generated by Django 4.2.13 on 2024-05-24 05:30

from django.db import migrations, models
import hub.models
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0040_auto_20220317_1124"),
    ]

    operations = [
        migrations.AlterField(
            model_name="blogpost",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="statement",
            field=models.FileField(
                blank=True,
                help_text="Declarație pe propria răspundere a reprezentantului desemnat prin care declară că nu este membru al conducerii unui partid politic, nu a fost ales într-o funcție publică și nu este demnitar al statului român.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Representative statement",
            ),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="status",
            field=model_utils.fields.StatusField(
                choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")],
                default="pending",
                max_length=100,
                no_check_for_status=True,
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="candidateconfirmation",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="candidatesupporter",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="candidatevote",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="city",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="domain",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="emailtemplate",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="featureflag",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="fiscal_certificate_anaf",
            field=models.FileField(
                blank=True,
                help_text="Certificat fiscal emis de ANAF",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Fiscal certificate ANAF",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="fiscal_certificate_local",
            field=models.FileField(
                blank=True,
                help_text="Certificat fiscal emis de Direcția de Impozite și Taxe Locale",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Fiscal certificate local",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="last_balance_sheet",
            field=models.FileField(
                max_length=300, null=True, upload_to="", verbose_name="First page of last balance sheet"
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="logo",
            field=models.ImageField(
                max_length=300, storage=hub.models.select_public_storage, upload_to="", verbose_name="Logo"
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="report_2017",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2017",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="report_2018",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2018",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="report_2019",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2019",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="report_2020",
            field=models.FileField(
                blank=True,
                help_text="Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Yearly report 2020",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="statement_discrimination",
            field=models.FileField(
                blank=True,
                help_text="Declarație pe proprie răspundere prin care declară că nu realizează activități sau susține cauze de natură politică sau care discriminează pe considerente legate de etnie, rasă, sex, orientare sexuală, religie, capacități fizice sau psihice sau de apartenența la una sau mai multe categorii sociale sau economice.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Non-discrimination statement",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="statement_political",
            field=models.FileField(
                blank=True,
                help_text="Declarație pe propria răspundere prin care declar că ONG-ul nu are între membrii conducerii organizației (Președinte sau Consiliul Director) membri ai conducerii unui partid politic sau persoane care au fost alese într-o funcție publică.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="Non-political statement",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="status",
            field=model_utils.fields.StatusField(
                choices=[("pending", "Pending approval"), ("accepted", "Accepted"), ("rejected", "Rejected")],
                default="pending",
                max_length=100,
                no_check_for_status=True,
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="statute",
            field=models.FileField(
                help_text="Copie a ultimului statut autentificat al organizației și a hotărârii judecătorești corespunzătoare, definitivă şi irevocabilă și copii ale tuturor documentelor ulterioare/suplimentare ale statutului, inclusiv hotărârile judecătorești definitive și irevocabile; Vă rugăm să arhivați documentele și să încărcați o singură arhivă în platformă.",
                max_length=300,
                null=True,
                upload_to="",
                verbose_name="NGO Statute",
            ),
        ),
    ]
