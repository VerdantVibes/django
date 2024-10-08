# Generated by Django 5.0.6 on 2024-06-25 02:46

import core.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, unique=True)),
                ('slug', models.CharField(help_text='e.g. shopify or yahoo_finance', max_length=64, unique=True)),
                ('client_id', models.CharField(blank=True, max_length=255, null=True)),
                ('client_secret', models.CharField(blank=True, max_length=255, null=True)),
                ('scopes', models.JSONField(blank=True, help_text='e.g. ["read_products", "read_customers"]', null=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='app_logo')),
                ('auth_method', models.CharField(blank=True, choices=[(None, ''), ('basic', 'Basic'), ('api_key', 'API Key'), ('oauth', 'OAuth')], max_length=64, null=True)),
                ('authorization_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/authorize', max_length=255, null=True)),
                ('token_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/access_token', max_length=255, null=True)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('is_own_app', models.BooleanField(default=True)),
                ('metadata', models.JSONField(blank=True, help_text='array of metadata, e.g. [{"label": "Store Name", "name": "store_name"}, {"label": "Account Type", "name": "account"}]', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DataSource',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, unique=True)),
                ('slug', models.CharField(help_text='e.g. shopify or yahoo_finance', max_length=64, unique=True)),
                ('client_id', models.CharField(blank=True, max_length=255, null=True)),
                ('client_secret', models.CharField(blank=True, max_length=255, null=True)),
                ('scopes', models.JSONField(blank=True, help_text='e.g. ["read_products", "read_customers"]', null=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='app_logo')),
                ('auth_method', models.CharField(blank=True, choices=[(None, ''), ('basic', 'Basic'), ('api_key', 'API Key'), ('oauth', 'OAuth')], max_length=64, null=True)),
                ('authorization_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/authorize', max_length=255, null=True)),
                ('token_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/access_token', max_length=255, null=True)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('is_own_app', models.BooleanField(default=True)),
                ('metadata', models.JSONField(blank=True, help_text='array of metadata, e.g. [{"label": "Store Name", "name": "store_name"}, {"label": "Account Type", "name": "account"}]', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=32)),
                ('org_info', models.TextField(blank=True, help_text='Share the story and mission of your organization. This will help us craft more personalized impact stories.', max_length=768, null=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='tenant_logo')),
                ('website', models.URLField(blank=True, help_text='for donation page', null=True)),
                ('support_email', models.EmailField(blank=True, help_text='for donation page', max_length=254, null=True)),
                ('ai_search_service_name', models.CharField(blank=True, max_length=128, null=True)),
                ('ai_search_index_name', models.CharField(blank=True, max_length=128, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('allowed_applications', models.ManyToManyField(blank=True, related_name='tenants', to='core.application')),
                ('allowed_data_sources', models.ManyToManyField(blank=True, related_name='tenants', to='core.datasource')),
            ],
        ),
        migrations.CreateModel(
            name='StoryRoom',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('enabled', models.BooleanField(default=True)),
                ('categories', models.JSONField(default=core.models.default_categories)),
                ('allow_donation', models.BooleanField(default=False)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='ReportBaseTemplate',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(help_text='title of template', max_length=255)),
                ('description', models.CharField(blank=True, help_text='description of template', max_length=255, null=True)),
                ('template_file', models.FileField(upload_to='base_report_template')),
                ('is_official', models.BooleanField(default=False)),
                ('is_approved', models.BooleanField(default=False)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(choices=[('PDF', 'PDF'), ('PPT', 'PPT')], default='PDF', max_length=32)),
                ('tenant', models.ForeignKey(blank=True, db_column='tenant_uuid', null=True, on_delete=django.db.models.deletion.CASCADE, to='core.tenant')),
            ],
            options={
                'ordering': ['-is_official', 'tenant', 'category', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('category', models.CharField(choices=[('question', 'Query'), ('donorReport', 'Donor Story'), ('grantReport', 'Grant Summary'), ('opsReport', 'Ops Insight')], default='bite', help_text='Data Bite or Data Story', max_length=64)),
                ('title', models.CharField(help_text='title of portfolio', max_length=255)),
                ('description', models.CharField(blank=True, help_text='description of portfolio', max_length=255, null=True)),
                ('html_file_key', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('user', models.ForeignKey(db_column='user_uuid', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, to_field='uuid')),
                ('tenant', models.ForeignKey(db_column='tenant_uuid', null=True, on_delete=django.db.models.deletion.CASCADE, to='core.tenant')),
            ],
            options={
                'verbose_name_plural': 'Portfolio',
            },
        ),
        migrations.CreateModel(
            name='Integration',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('auth_info', models.JSONField(help_text='{"access_token": "aaaa"}', null=True)),
                ('access_token_expires_at', models.DateTimeField(blank=True, help_text='e.g. quickbooks token expires in 1 hour', null=True)),
                ('refresh_token', models.TextField(blank=True, null=True)),
                ('refresh_token_expires_at', models.DateTimeField(blank=True, help_text='e.g. quickbooks token expires in 100 days', null=True)),
                ('other_info', models.JSONField(blank=True, help_text='{"store_name": "cccc", "realm_id": "dddd", "base_url":"eeee"}', null=True)),
                ('client_id', models.CharField(blank=True, max_length=255, null=True)),
                ('client_secret', models.CharField(blank=True, max_length=255, null=True)),
                ('scopes', models.JSONField(blank=True, help_text='e.g. ["read_products", "read_customers"]', null=True)),
                ('authorization_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/authorize', max_length=255, null=True)),
                ('token_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/access_token', max_length=255, null=True)),
                ('application', models.CharField(default='shopify', help_text='which application is this integration for', max_length=64)),
                ('tenant', models.ForeignKey(db_column='tenant_uuid', null=True, on_delete=django.db.models.deletion.CASCADE, to='core.tenant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('mode', models.CharField(max_length=64)),
                ('amount', models.IntegerField()),
                ('donate_as', models.CharField(max_length=128)),
                ('cover_fees', models.BooleanField(default=False)),
                ('status', models.CharField(max_length=128)),
                ('subscription', models.CharField(blank=True, help_text='subscription ID of Stripe', max_length=128, null=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='DataConnection',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('auth_info', models.JSONField(help_text='{"access_token": "aaaa"}', null=True)),
                ('access_token_expires_at', models.DateTimeField(blank=True, help_text='e.g. quickbooks token expires in 1 hour', null=True)),
                ('refresh_token', models.TextField(blank=True, null=True)),
                ('refresh_token_expires_at', models.DateTimeField(blank=True, help_text='e.g. quickbooks token expires in 100 days', null=True)),
                ('other_info', models.JSONField(blank=True, help_text='{"store_name": "cccc", "realm_id": "dddd", "base_url":"eeee"}', null=True)),
                ('client_id', models.CharField(blank=True, max_length=255, null=True)),
                ('client_secret', models.CharField(blank=True, max_length=255, null=True)),
                ('scopes', models.JSONField(blank=True, help_text='e.g. ["read_products", "read_customers"]', null=True)),
                ('authorization_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/authorize', max_length=255, null=True)),
                ('token_url', models.CharField(blank=True, help_text='e.g. https://{store}.myshopify.com/admin/oauth/access_token', max_length=255, null=True)),
                ('data_source', models.CharField(default='sharepoint', help_text='which data source is this connection for', max_length=64)),
                ('tenant', models.ForeignKey(db_column='tenant_uuid', on_delete=django.db.models.deletion.CASCADE, to='core.tenant')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
