import os
from urllib.parse import quote
from opencensus.ext.azure.log_exporter import AzureLogHandler

from .settings import *
from .settings import BASE_DIR

# Configure the domain name using the environment variable
# that Azure automatically creates for us.
ALLOWED_HOSTS = [
    os.environ['WEBSITE_HOSTNAME'],
    'admin.getcadenza.com',
    'app.getcadenza.com',
    'admin.cadenzaa.com',
    'app.cadenzaa.com',
    '169.254.130.1',
    '169.254.130.2',
    '169.254.130.3',
    '169.254.130.4',
    '169.254.130.5',
    '169.254.130.6',
    '169.254.130.7',
    '169.254.130.8',
    '169.254.130.9',
] if 'WEBSITE_HOSTNAME' in os.environ else []
CSRF_TRUSTED_ORIGINS = [
    'https://' + os.environ['WEBSITE_HOSTNAME'],
    'https://cadenzaa.azurewebsites.net',
    'https://app.getcadenza.com',
    'https://admin.getcadenza.com',
    'https://app.cadenzaa.com',
    'https://admin.cadenzaa.com',
] if 'WEBSITE_HOSTNAME' in os.environ else []
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://cadenzaa.azurewebsites.net",
    "https://app.getcadenza.com",
    "https://admin.getcadenza.com",
    "https://app.cadenzaa.com",
    "https://admin.cadenzaa.com",
]

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "connection_string": os.environ['AZURE_STORAGE_CONNECTION_STRING'],
            "azure_container": "django-media-prod",
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Configure Postgres database based on connection string of the libpq Keyword/Value form
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
conn_str = os.environ['AZURE_POSTGRESQL_CONNECTIONSTRING']
conn_str_params = {pair.split('=')[0]: pair.split('=')[1] for pair in conn_str.split(' ')}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': conn_str_params['dbname'],
        'HOST': conn_str_params['host'],
        'USER': conn_str_params['user'],
        'PASSWORD': conn_str_params['password'],
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'azure': {
            'level': 'INFO',
            'class': 'opencensus.ext.azure.log_exporter.AzureLogHandler',
            'instrumentation_key': 'b3b4c143-a754-412e-abd4-993e38c54032',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'azure'],
            'level': 'INFO',
        },
    },
}

AZURE_STORAGE_CONNECTION_STRING = os.environ['AZURE_STORAGE_CONNECTION_STRING']
AZURE_STORAGE_REPORT_CONTAINER_NAME = 'django-prod'
AZURE_STORAGE_MEDIA_CONTAINER_NAME = 'django-media-prod'

AZURE_STORAGE_RAG_CONNECTION_STRING = os.environ['AZURE_STORAGE_RAG_CONNECTION_STRING']
AZURE_STORAGE_RAG_CONTAINER_NAME = 'sync-storage-prod'

AZURE_COMMUNICATION_CONNECTION_STRING = os.environ['AZURE_COMMUNICATION_CONNECTION_STRING']

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']

EXA_API_KEY = os.environ['EXA_API_KEY']
