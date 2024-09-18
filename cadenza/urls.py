"""
URL configuration for cadenza project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
from rest_framework.authtoken.models import TokenProxy

admin.site.site_header = 'Cadenza Administration'
admin.site.index_title = 'Cadenza Administration'
admin.site.site_title = 'Cadenza Administration'

models_to_unregister = [
    Group,
    EmailAddress,
    Site,
    SocialAccount,
    SocialToken,
    SocialApp,
    TokenProxy,
]

for model in models_to_unregister:
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass

urlpatterns = [
    path('admin/', admin.site.urls),
    path('select2/', include('django_select2.urls')),
    path('api/auth/', include('authentication.urls')),
    path('api/oauth/', include('oauth.urls')),
    path('api/core/', include('core.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('user_activity/', include('user_activity.urls')),  

]
