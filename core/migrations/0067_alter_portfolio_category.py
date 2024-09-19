# Generated by Django 5.0.6 on 2024-07-31 01:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0066_portfolio_report_id_alter_portfolio_category_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portfolio',
            name='category',
            field=models.CharField(choices=[('impactReport', 'Impact Report')], default='impactReport', help_text='Impact Report', max_length=64),
        ),
    ]
