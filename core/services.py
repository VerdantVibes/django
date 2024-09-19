import pytz
import logging
from datetime import datetime, timedelta

from django.utils import timezone

from core import models

logger = logging.getLogger(__name__)


class DataConnectionService:
    def __init__(self, data_connection_uuid=None, data_connection=None, tenant_uuid=None) -> None:
        self.data_connection = None
        if data_connection_uuid:
            self.data_connection = models.DataConnection.objects.filter(uuid=data_connection_uuid).first()
        if data_connection:
            self.data_connection = data_connection
        if not self.data_connection:
            logger.info(f"DataConnection not found while creating DataConnectionService: {data_connection_uuid}")
        self.tenant_uuid = tenant_uuid

    @classmethod
    def _refresh(cls, data_connection):
        from oauth.services import OAuthService
        data_source_slug = data_connection.data_source
        data_source_instance = models.DataSource.objects.get(slug=data_source_slug)
        oauth_info = None
        if not data_source_instance.is_own_app:
            oauth_info = {
                'client_id': data_connection.client_id,
                'client_secret': data_connection.client_secret,
                'scopes': data_connection.scopes,
                'authorization_url': data_connection.authorization_url,
                'token_url': data_connection.token_url
            }
        service = OAuthService(application_slug=data_source_slug, is_data_source=True, token={'refresh_token': data_connection.refresh_token}, oauth_info=oauth_info)
        result = service.refresh_token()
        access_token = result.get('access_token')
        refresh_token = result.get('refresh_token')
        x_refresh_token_expires_in = result.get('x_refresh_token_expires_in')
        expires_at = result.get('expires_at')
        if data_connection.auth_info is None:
            data_connection.auth_info = {}
        data_connection.auth_info['access_token'] = access_token
        data_connection.refresh_token = refresh_token
        if x_refresh_token_expires_in:  # NOTE: different connector may return different name, or no such value for long-lived
            data_connection.refresh_token_expires_at = timezone.now() + timedelta(seconds=x_refresh_token_expires_in)
        data_connection.access_token_expires_at = datetime.fromtimestamp(expires_at, pytz.UTC)
        data_connection.save()
        logger.info(f"IntegrationService: refreshed token for {data_connection}")
    
    def refresh_token(self):
        if self.data_connection is None or self.data_connection.access_token_expires_at is None:
            return
        logger.info(f"refrsh oauth token: {self.data_connection}")
        self._refresh(self.data_connection)
    
    def refresh_all(self):
        """refresh integrations of the tenant"""
        if self.tenant_uuid is None:
            return
        integrations = models.Integration.objects.filter(tenant_id=self.tenant_uuid, access_token_expires_at__isnull=False)
        for integration in integrations:
            self._refresh(integration)
            logger.info(f"refrsh oauth token: {integration}")
