# Generated by Django 5.0.6 on 2024-07-12 00:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_releasenote'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tenant',
            name='allowed_applications',
        ),
    ]