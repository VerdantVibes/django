from rest_framework import permissions as rest_permissions
from core import models as core_models


class CadenzaAdminPermission(rest_permissions.BasePermission):
    """check if user is Candenza admin"""

    def has_permission(self, request, view):
        return request.user.is_cadenza_admin


class TenantAdminPermission(rest_permissions.BasePermission):
    """check if user is Tenant admin"""

    def has_permission(self, request, view):
        return request.user.is_tenant_admin
    
    def has_object_permission(self, request, view, obj):
        """current admin user and the obj user come from same tenant"""
        if isinstance(obj, core_models.Tenant):
            return request.user.tenant == obj
        return request.user.tenant == obj.tenant
