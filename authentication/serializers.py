from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import serializers
from allauth.account.utils import setup_user_email
from allauth.account.adapter import get_adapter
from dj_rest_auth import serializers as dj_serializers
from dj_rest_auth.registration import serializers as dj_register_serializers

from core.models import Tenant

UserModel = get_user_model()


class UserDetailsSerializer(dj_serializers.UserDetailsSerializer):
    """Custom UserDetailsSerializer, add role, tenant ID, tenant name"""
    role = serializers.SerializerMethodField()
    tenant_id = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    story_room_enabled = serializers.SerializerMethodField()

    def get_role(self, obj):
        if obj.is_tenant_admin:
            return 'tenant-admin'
        elif obj.is_cadenza_admin:
            return 'cadenza-admin'
        else:
            return 'assistant'

    def get_tenant_id(self, obj):
        if obj.tenant is not None:
            return obj.tenant.uuid
        return None  # or some default value

    def get_tenant_name(self, obj):
        if obj.tenant is not None:
            return obj.tenant.name
        return None  # or some default value

    def get_story_room_enabled(self, obj):
        if obj.tenant is not None:
            return obj.tenant.storyroom_set.filter(enabled=True).exists()
        return False

    class Meta:
        extra_fields = []
        # see https://github.com/iMerica/dj-rest-auth/issues/181
        # UserModel.XYZ causing attribute error while importing other
        # classes from `serializers.py`. So, we need to check whether the auth model has
        # the attribute or not
        if hasattr(UserModel, 'USERNAME_FIELD'):
            extra_fields.append(UserModel.USERNAME_FIELD)
        if hasattr(UserModel, 'EMAIL_FIELD'):
            extra_fields.append(UserModel.EMAIL_FIELD)
        if hasattr(UserModel, 'first_name'):
            extra_fields.append('first_name')
        if hasattr(UserModel, 'last_name'):
            extra_fields.append('last_name')
        model = UserModel
        fields = ('pk', 'role', 'tenant_id', 'tenant_name', 'story_room_enabled', *extra_fields)
        read_only_fields = ('email', 'role', 'tenant_id', 'tenant_name', 'story_room_enabled')


class CustomDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return value.strftime('%Y-%m-%d.%H:%M') if value else None


class UserSerializer(serializers.ModelSerializer):
    """show list of sub-accounts for Tenant Admin"""
    date_joined = CustomDateTimeField()

    class Meta:
        model = UserModel
        fields = ['id', 'first_name', 'last_name', 'email', 'is_active', 'date_joined', 'is_tenant_admin', 'job_title']


class UserAddingSerializer(serializers.ModelSerializer):
    """add user of Tenant"""
    password1 = serializers.CharField(max_length=128)
    password2 = serializers.CharField(max_length=128)
    is_tenant_admin = serializers.CharField(max_length=3)
    job_title = serializers.CharField(max_length=128)

    class Meta:
        model = UserModel
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2', 'is_tenant_admin', 'job_title']
    
    def validate(self, data):
        """
        Check 2 password equal.
        """
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("please enter same password twice")
        return data


class UserDisableEnableSerializer(serializers.ModelSerializer):
    """disable/enable sub-account of Tenant Admin"""
    class Meta:
        model = UserModel
        fields = ['is_active']


class ChangePasswordSerializer(serializers.Serializer):
    """teant admin can change password of sub-account"""
    password1 = serializers.CharField(max_length=128)
    password2 = serializers.CharField(max_length=128)

    def validate(self, data):
        """
        Check 2 password equal.
        """
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("please enter same password twice")
        return data


class TenantSerializer(serializers.ModelSerializer):
    """show tenant details, for Tenant Admin"""
    class Meta:
        model = Tenant
        fields = [
            'uuid', 'name', 'email', 'phone',
            'allowed_data_sources', 'org_info', 'website',
            'support_email', 'news_topics', 'primary_location', 'created_at'
        ]

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(max_length=128)
    token = serializers.CharField()
    uidb64 = serializers.CharField()