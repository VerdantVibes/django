import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User"""
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email address", unique=True, blank=True)
    tenant = models.ForeignKey("core.Tenant", db_column="tenant_uuid", on_delete=models.CASCADE, null=True)
    is_tenant_admin = models.BooleanField(default=False)
    is_cadenza_admin = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    job_title = models.CharField(max_length=128, null=True, blank=True, help_text="Job Title/Function")

    REQUIRED_FIELDS = ["first_name", "last_name"]
    USERNAME_FIELD = "email"

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        if self.is_cadenza_admin:
            self.is_superuser = True
            self.is_staff = True
        super().save(*args, **kwargs)
