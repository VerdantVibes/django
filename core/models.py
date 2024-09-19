import uuid
import logging
import requests

from django.db import models
from django.conf import settings

PORTFOLIO_CATEGORIES = (
    ('impactReport', 'Impact Report'),
)

AUTH_METHODS = (
    (None, ''),
    ('basic', 'Basic'),
    ('api_key', 'API Key'),
    ('oauth', 'OAuth'),
)

REPORT_BASE_TEMPLATE_CATEGORY = (
    ('PDF', 'PDF'),
    ('PPT', 'PPT'),
)

logger = logging.getLogger(__name__)


class Tenant(models.Model):
    """business info"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    allowed_data_sources = models.ManyToManyField(to="core.DataSource", related_name="tenants", blank=True)
    org_info = models.TextField(max_length=768, null=True, blank=True, 
                             help_text="Share the story and mission of your organization. This will help us craft more personalized impact stories.")
    logo = models.ImageField(upload_to='tenant_logo', null=True, blank=True)
    website = models.URLField(null=True, blank=True, help_text="for donation page")
    support_email = models.EmailField(null=True, blank=True, help_text="for donation page")
    news_topics = models.CharField(max_length=128, null=True, blank=True, help_text="What kind of news topics would be most helpful")
    primary_location = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ai_search_service_name = models.CharField(max_length=128, null=True, blank=True)
    ai_search_index_name = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return self.name


def default_categories():
    """default value of JSONField must be callable"""
    return ["testimonial", "quick moments", "experiences", "other"]


class StoryRoom(models.Model):
    """CZ-107, story room info"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enabled = models.BooleanField(default=True)
    categories = models.JSONField(default=default_categories)
    allow_donation = models.BooleanField(default=False)
    tenant = models.ForeignKey("Tenant", on_delete=models.CASCADE)

    def __str__(self):
        return self.tenant.name


class Donation(models.Model):
    """CZ-125, donation info"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mode = models.CharField(max_length=64)
    amount = models.IntegerField()
    donate_as = models.CharField(max_length=128)
    cover_fees = models.BooleanField(default=False)
    status = models.CharField(max_length=128)
    subscription = models.CharField(max_length=128, null=True, blank=True, help_text="subscription ID of Stripe")
    tenant = models.ForeignKey("Tenant", on_delete=models.CASCADE)

    def __str__(self):
        return self.tenant.name


class BaseApplication(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    slug = models.CharField(max_length=64, unique=True, help_text="e.g. shopify or yahoo_finance")
    client_id = models.CharField(max_length=255, null=True, blank=True)
    client_secret = models.CharField(max_length=255, null=True, blank=True)
    scopes = models.JSONField(help_text='e.g. ["read_products", "read_customers"]', null=True, blank=True)
    logo = models.ImageField(upload_to='app_logo', null=True, blank=True)
    auth_method = models.CharField(max_length=64, choices=AUTH_METHODS, null=True, blank=True)
    authorization_url = models.CharField(max_length=255, null=True, blank=True, help_text="e.g. https://{store}.myshopify.com/admin/oauth/authorize")
    token_url = models.CharField(max_length=255, null=True, blank=True, help_text="e.g. https://{store}.myshopify.com/admin/oauth/access_token")
    description = models.CharField(max_length=255, null=True, blank=True)
    is_own_app = models.BooleanField(default=True)
    metadata = models.JSONField(
        help_text='array of metadata, e.g. [{"label": "Store Name", "name": "store_name"}, {"label": "Account Type", "name": "account"}]',
        null=True,
        blank=True)
    
    class Meta:
        abstract = True


class DataSource(BaseApplication):
    """SharePoint, Dropbox, etc, maintained by Cadenza Admin manually"""

    def __str__(self) -> str:
        return f"{self.pk} {self.name}"


class BaseIntegration(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_info = models.JSONField(null=True, help_text='{"access_token": "aaaa"}')
    access_token_expires_at = models.DateTimeField(null=True,
                                                   blank=True,
                                                   help_text="e.g. quickbooks token expires in 1 hour")
    refresh_token = models.TextField(null=True, blank=True)
    refresh_token_expires_at = models.DateTimeField(null=True,
                                                    blank=True,
                                                    help_text="e.g. quickbooks token expires in 100 days")
    other_info = models.JSONField(null=True, blank=True,
                                  help_text='{"store_name": "cccc", "realm_id": "dddd", "base_url":"eeee"}')

    # if application.is_own_app is False, we need to save the following here:
    client_id = models.CharField(max_length=255, null=True, blank=True)
    client_secret = models.CharField(max_length=255, null=True, blank=True)
    scopes = models.JSONField(help_text='e.g. ["read_products", "read_customers"]', null=True, blank=True)
    authorization_url = models.CharField(max_length=255, null=True, blank=True, help_text="e.g. https://{store}.myshopify.com/admin/oauth/authorize")
    token_url = models.CharField(max_length=255, null=True, blank=True, help_text="e.g. https://{store}.myshopify.com/admin/oauth/access_token")
    
    class Meta:
        abstract = True


class DataConnection(BaseIntegration):
    """tenant's auth info"""
    tenant = models.ForeignKey("Tenant", db_column="tenant_uuid", on_delete=models.CASCADE)
    data_source = models.CharField(max_length=64,
                                   default='sharepoint',
                                   help_text='which data source is this connection for')

    def __str__(self) -> str:
        return f"{self.pk} {self.tenant.name}"
    
    def delete(self, *args, **kwargs):
        if self.data_source == "googledrive":
            access_token = self.auth_info.get("access_token")
            revoke_token_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
            requests.post(revoke_token_url)
        super().delete(*args, **kwargs)


class Portfolio(models.Model):
    """all the Data Bites and Data Stories"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("Tenant", db_column="tenant_uuid", on_delete=models.CASCADE, null=True)
    user = models.ForeignKey("authentication.User", db_column="user_uuid", to_field='uuid', on_delete=models.CASCADE, null=True)
    category = models.CharField(max_length=64,
                                choices=PORTFOLIO_CATEGORIES,
                                default='impactReport',
                                help_text='Impact Report')
    title = models.CharField(max_length=255, help_text='title of portfolio')
    description = models.CharField(max_length=255, help_text='description of portfolio', null=True, blank=True)
    html_file_key = models.CharField(max_length=255, null=True, blank=True)
    report_id = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, auto_now=True)

    class Meta:
        verbose_name_plural = "Portfolio"

    def __str__(self) -> str:
        return f"{self.pk} {self.title}"
    
    @classmethod
    def getReportIDForUser(self, report_id, tenant_uuid, user):
        # Find record with report id and user id
        instance = self.objects.filter(
            report_id=report_id,
            category='impactReport',
        ).first()

        # If exist send response (---end---)
        if instance: 
            if instance.tenant_id != tenant_uuid:
                return { "status": False, "code": "not_allowed" }
            else:
                return { "status": True, "instance": instance }
        else:
            # IF not exist check with llm agent

            # Call External LLM - Get Report - START
            request_url = settings.LLM_AGENT_ENDPOINTS['GetReport'].format(report_id=report_id)
            response = requests.get(request_url)
            # Call External LLM - Get Report - END

            # If exist with llm, create record & send response (---end---)
            if(response.status_code == 200):
                response_data = response.json()

                if response_data['tenant_id'] == tenant_uuid:
                    # Get Report title > Markdown to html > find title from html
                    report_title='-'


                    instance = models.Portfolio.objects.create(
                        report_id=report_id,
                        tenant_id=tenant_uuid,
                        user=user,
                        category='impactReport',
                        title=report_title
                    )
                    return { "status": True, "instance": instance }
                else:
                    return {"status": False, "code": tenant_uuid}
            else:
                # If not exist send false response
                return {"status": False, "code": "something_went_wrong"}


class ReportBaseTemplate(models.Model):
    """
    user uploaded template,
    https://cadenzaa.atlassian.net/browse/CZ-72
    https://cadenzaa.atlassian.net/browse/CZ-79
    https://cadenzaa.atlassian.net/browse/CZ-117
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text='title of template')
    description = models.CharField(max_length=255, help_text='description of template', null=True, blank=True)
    template_file = models.FileField(upload_to='base_report_template')
    tenant = models.ForeignKey("Tenant", db_column="tenant_uuid", on_delete=models.CASCADE, null=True, blank=True)
    is_official = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(max_length=32, choices=REPORT_BASE_TEMPLATE_CATEGORY, default='PDF')

    class Meta:
        ordering = ["-is_official", "tenant", "category", "created_at"]

    def __str__(self) -> str:
        return f"{self.pk} {self.title}"


class ReleaseNote(models.Model):
    """CZ-153 show release notes on dashboard"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    heading = models.CharField(max_length=255)
    sub_heading = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(max_length=768, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
