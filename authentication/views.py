import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError

from authentication import serializers as auth_serializers
from authentication.permissions import TenantAdminPermission
from core import models as core_models
from core import utils


logger = logging.getLogger(__name__)

UserModel = get_user_model()


class AccountListView(generics.ListAPIView):
    serializer_class = auth_serializers.UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant = user.tenant
        return UserModel.objects.filter(tenant=tenant, is_visible=True)


class AccountAddView(generics.CreateAPIView):
    serializer_class = auth_serializers.UserAddingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.data
        try:
            UserModel.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password1'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                job_title=data['job_title'],
                tenant=user.tenant,
                is_tenant_admin=data['is_tenant_admin'] == 'on'
            )
        except IntegrityError:
            raise ValidationError({'email': ['the account already exists']})


class AccountEnableDisableView(generics.UpdateAPIView):
    serializer_class = auth_serializers.UserDisableEnableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """make sure the user and the admin user come from same Tenant"""
        user = self.request.user
        return UserModel.objects.filter(tenant=user.tenant)


class ChangePasswordView(APIView):
    serializer_class = auth_serializers.ChangePasswordSerializer
    permission_classes = [IsAuthenticated, TenantAdminPermission]

    def post(self, request, format=None, *args, **kwargs):
        pk = kwargs['pk']
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            new_password = serializer.data['password1']
            user = UserModel.objects.get(pk=pk)
            self.check_object_permissions(request, user)
            user.set_password(new_password)
            user.save()
            return Response('ok', status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(generics.GenericAPIView):
    serializer_class = auth_serializers.PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = UserModel.objects.filter(email=email).first()
        if user:
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"{settings.FRONTEND_DOMAIN}/auth/reset-password-confirm/{uidb64}/{token}/"

            utils.send_email(
                email,
                "Reset password",
                f'Click the link to reset your password: {reset_link}'
            )
        return Response({"message": "Password reset link sent."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = auth_serializers.PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['new_password']
        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = UserModel.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid token or user."}, status=status.HTTP_400_BAD_REQUEST)


class DeleteUserView(APIView):
    """Mark a user as deleted - inactive and invisible."""
    permission_classes = [IsAuthenticated, TenantAdminPermission]

    def delete(self, request, format=None, *args, **kwargs):
        pk = kwargs['pk']
        current_user = request.user
        user = UserModel.objects.get(pk=pk)
        if user.tenant == current_user.tenant:
            user.is_active = False
            user.is_visible = False
            if not user.email.startswith('DELETE'):
                user.email = f'DELETE-{user.pk}-{user.email}'
            user.save()
        return Response('ok', status=status.HTTP_200_OK)


class TenantView(generics.RetrieveUpdateAPIView):
    """show/edit `story` of tenant"""
    permission_classes = [IsAuthenticated, TenantAdminPermission]
    queryset = core_models.Tenant.objects.all()
    serializer_class = auth_serializers.TenantSerializer

    def get_object(self):
        current_user = self.request.user
        return current_user.tenant
