# Generated by Django 5.2.2 on 2025-07-05 04:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='action_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
