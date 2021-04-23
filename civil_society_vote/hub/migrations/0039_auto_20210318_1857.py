# Generated by Django 2.2.19 on 2021-03-18 16:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0038_election'),
    ]

    operations = [
        migrations.AddField(
            model_name='domain',
            name='election',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='hub.Election'),
        ),
        migrations.AddField(
            model_name='organization',
            name='election',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='hub.Election'),
        ),
    ]
