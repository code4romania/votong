# Generated by Django 2.2.12 on 2020-05-19 21:49

from django.conf import settings
import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('name', models.CharField(max_length=254, verbose_name='Name')),
                ('role', models.CharField(max_length=254, verbose_name='Name')),
                ('experience', models.TextField(verbose_name='Profesional experience')),
                ('studies', models.TextField(verbose_name='Studies')),
                ('founder', models.BooleanField(default=False, verbose_name='Founder/Associate')),
                ('representative', models.BooleanField(default=False, verbose_name='Legal representative')),
                ('board_member', models.BooleanField(default=False, verbose_name='Board member')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('phone', models.CharField(max_length=30, verbose_name='Phone')),
                ('photo', models.ImageField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Photo')),
                ('domain', models.PositiveSmallIntegerField(choices=[(1, 'Organizații academice și profesionale'), (2, 'Organizații din domeniul sănătății/educației'), (3, 'Organizații cooperatiste și agricole'), (4, 'Organizații din domeniul mediului'), (5, 'Organizații din domeniul social, familia și persoane cu dizabiltăți și pensionari'), (6, 'Organizații pentru Protecția Drepturilor Omului')], verbose_name='Domain')),
                ('mandate', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Mandate from the organizaion')),
                ('letter', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Letter of intent')),
                ('statement', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Steatement of conformity')),
                ('cv', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='CV')),
                ('legal_record', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Legal record')),
            ],
            options={
                'verbose_name': 'Candidate',
                'verbose_name_plural': 'Candidates',
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=100, verbose_name='City')),
                ('county', models.CharField(max_length=50, verbose_name='County')),
                ('is_county_residence', models.BooleanField(default=False, verbose_name='Is county residence')),
            ],
            options={
                'verbose_name': 'City',
                'verbose_name_plural': 'cities',
                'unique_together': {('city', 'county')},
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('name', models.CharField(max_length=254, verbose_name='NGO Name')),
                ('domain', models.PositiveSmallIntegerField(choices=[(1, 'Organizații academice și profesionale'), (2, 'Organizații din domeniul sănătății/educației'), (3, 'Organizații cooperatiste și agricole'), (4, 'Organizații din domeniul mediului'), (5, 'Organizații din domeniul social, familia și persoane cu dizabiltăți și pensionari'), (6, 'Organizații pentru Protecția Drepturilor Omului')], verbose_name='Domain')),
                ('reg_com_number', models.CharField(max_length=20, verbose_name='Registration number')),
                ('status', models.CharField(choices=[('active', 'active'), ('inactive', 'inactive')], default='active', max_length=10, verbose_name='Current status')),
                ('purpose_initial', models.CharField(max_length=254, verbose_name='Initial purpose')),
                ('purpose_current', models.CharField(max_length=254, verbose_name='Current purpose')),
                ('founders', models.CharField(max_length=254, verbose_name='Founders/Associates')),
                ('representative', models.CharField(max_length=254, verbose_name='Legal representative')),
                ('board_council', models.CharField(max_length=254, verbose_name='Board council')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('phone', models.CharField(max_length=30, verbose_name='Phone')),
                ('county', models.CharField(choices=[('Alba', 'Alba'), ('Arad', 'Arad'), ('Arges', 'Arges'), ('Bacau', 'Bacau'), ('Bihor', 'Bihor'), ('Bistrita-Nasaud', 'Bistrita-Nasaud'), ('Botosani', 'Botosani'), ('Braila', 'Braila'), ('Brasov', 'Brasov'), ('Bucuresti', 'Bucuresti'), ('Buzau', 'Buzau'), ('Caras-Severin', 'Caras-Severin'), ('Calarasi', 'Calarasi'), ('Cluj', 'Cluj'), ('Constanta', 'Constanta'), ('Covasna', 'Covasna'), ('Dambovita', 'Dambovita'), ('Dolj', 'Dolj'), ('Galati', 'Galati'), ('Giurgiu', 'Giurgiu'), ('Gorj', 'Gorj'), ('Harghita', 'Harghita'), ('Hunedoara', 'Hunedoara'), ('Ialomita', 'Ialomita'), ('Iasi', 'Iasi'), ('Ilfov', 'Ilfov'), ('Maramures', 'Maramures'), ('Mehedinti', 'Mehedinti'), ('Mures', 'Mures'), ('Neamt', 'Neamt'), ('Olt', 'Olt'), ('Prahova', 'Prahova'), ('Satu Mare', 'Satu Mare'), ('Salaj', 'Salaj'), ('Sibiu', 'Sibiu'), ('Suceava', 'Suceava'), ('Teleorman', 'Teleorman'), ('Timis', 'Timis'), ('Tulcea', 'Tulcea'), ('Vaslui', 'Vaslui'), ('Valcea', 'Valcea'), ('Vrancea', 'Vrancea')], max_length=50, verbose_name='County')),
                ('address', models.CharField(max_length=254, verbose_name='Address')),
                ('logo', models.ImageField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Logo')),
                ('last_balance_sheet', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='First page of last balance sheet')),
                ('statute', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='NGO Statute')),
                ('letter', models.FileField(max_length=300, storage=django.core.files.storage.FileSystemStorage(), upload_to='', verbose_name='Letter of intent')),
                ('registration_status', models.CharField(choices=[('pending', 'pending'), ('accepted', 'accepted'), ('rejected', 'rejected')], default='pending', max_length=10, verbose_name='Registration status')),
                ('city', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='hub.City', verbose_name='City')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Organization',
                'verbose_name_plural': 'Organizations',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='OrganizationVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('domain', models.PositiveSmallIntegerField(choices=[(1, 'Organizații academice și profesionale'), (2, 'Organizații din domeniul sănătății/educației'), (3, 'Organizații cooperatiste și agricole'), (4, 'Organizații din domeniul mediului'), (5, 'Organizații din domeniul social, familia și persoane cu dizabiltăți și pensionari'), (6, 'Organizații pentru Protecția Drepturilor Omului')], verbose_name='Domain')),
                ('vote', models.CharField(choices=[('YES', 'YES'), ('NO', 'NO'), ('ABSTENTION', 'ABSTENTION')], default='ABSTENTION', max_length=10, verbose_name='Vote')),
                ('motivation', models.TextField(blank=True, help_text='Motivate your decision', max_length=500, null=True, verbose_name='Motivation')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='hub.Organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Organization vote',
                'verbose_name_plural': 'Organization votes',
            },
        ),
        migrations.CreateModel(
            name='CandidateVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('domain', models.PositiveSmallIntegerField(choices=[(1, 'Organizații academice și profesionale'), (2, 'Organizații din domeniul sănătății/educației'), (3, 'Organizații cooperatiste și agricole'), (4, 'Organizații din domeniul mediului'), (5, 'Organizații din domeniul social, familia și persoane cu dizabiltăți și pensionari'), (6, 'Organizații pentru Protecția Drepturilor Omului')], verbose_name='Domain')),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='hub.Candidate')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Organization vote',
                'verbose_name_plural': 'Organization votes',
            },
        ),
        migrations.AddField(
            model_name='candidate',
            name='org',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='hub.Organization'),
        ),
        migrations.AddConstraint(
            model_name='organizationvote',
            constraint=models.UniqueConstraint(fields=('user', 'org'), name='unique_org_vote'),
        ),
        migrations.AddConstraint(
            model_name='organizationvote',
            constraint=models.UniqueConstraint(fields=('user', 'domain'), name='unique_org_domain_vote'),
        ),
        migrations.AlterUniqueTogether(
            name='organizationvote',
            unique_together={('user', 'org'), ('user', 'domain')},
        ),
        migrations.AddConstraint(
            model_name='candidatevote',
            constraint=models.UniqueConstraint(fields=('user', 'candidate'), name='unique_candidate_vote'),
        ),
        migrations.AddConstraint(
            model_name='candidatevote',
            constraint=models.UniqueConstraint(fields=('user', 'domain'), name='unique_candidate_domain_vote'),
        ),
    ]
