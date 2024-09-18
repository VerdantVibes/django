import os
from django.core.asgi import get_asgi_application

# Check for the WEBSITE_HOSTNAME environment variable to see if we are running in Azure Ap Service
# If so, then load the settings from production.py
settings_module = 'cadenza.production' if 'WEBSITE_HOSTNAME' in os.environ else 'cadenza.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
    }
)
