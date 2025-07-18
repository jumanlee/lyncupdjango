# Generated by Django 5.1.2 on 2025-05-29 15:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_appuser_is_verified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organisation',
            name='citytown',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='citytown',
        ),
        migrations.AlterField(
            model_name='organisation',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='organisation', to='users.country'),
        ),
    ]
