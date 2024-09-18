from typing import Any
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from authentication.models import User


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance
    return Wrapper


class UserChangeForm(BaseUserChangeForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["password"].widget.template_name = "auth/widgets/read_only_password_hash.html"
        self.fields["password"].help_text = f'<a href="../../{self.instance.pk}/password/">Change Password</a>'

class UserCreationForm(BaseUserCreationForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = (
            "email", "first_name", "last_name", "tenant",
            "is_tenant_admin", "is_cadenza_admin", "is_visible", "job_title"
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            if hasattr(self, "save_m2m"):
                self.save_m2m()
        return user


class UserAdmin(BaseUserAdmin):
    list_display = ('uuid', 'email', 'first_name', 'last_name', 'get_tenant', 'is_tenant_admin', 'is_cadenza_admin')
    search_fields = ["tenant__name", "first_name", "last_name", "email"]
    list_filter = ["is_tenant_admin", "is_cadenza_admin", "is_active", ("tenant__name", custom_titled_filter('Tenant Name')),]
    search_help_text = "Search by Tenant Name, First Name, Last Name, Email"

    form = UserChangeForm
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Personal info", {"fields": ["first_name", "last_name", "tenant", "job_title"]}),
        ("Permissions", {"fields": ["is_active", "is_visible", "is_tenant_admin", "is_cadenza_admin"]}),
    ]

    add_form = UserCreationForm
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": [
                    "email", "password1", "password2", "first_name",
                    "last_name", "tenant", "is_tenant_admin", "is_cadenza_admin",
                    "is_visible", "job_title"],
            },
        ),
    ]

    @admin.display(description='Tenant')
    def get_tenant(self, obj):
        return obj.tenant.name if obj.tenant else ''


admin.site.register(User, UserAdmin)
