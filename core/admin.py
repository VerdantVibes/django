from django.contrib import admin
from django.http import HttpResponseRedirect
from django import forms
from django_select2.forms import Select2Widget
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from core import models
from core.services import DataConnectionService


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance
    return Wrapper


class TenantAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'email', 'phone', 'created_at', 'ai_search_service_name', 'ai_search_index_name')
    model = models.Tenant


class StoryRoomAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'enabled', 'categories', 'tenant')
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
    model = models.StoryRoom


class DonationAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'mode', 'amount', 'donate_as', 'cover_fees', 'status', 'tenant')
    model = models.Donation


class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'title', 'category', 'get_tenant', 'get_user', 'created_at', 'updated_at')
    search_fields = ["tenant__name", "user__email", 'title', 'description']
    list_filter = [("tenant__name", custom_titled_filter('Tenant Name')),]
    search_help_text = "Search by Tenant Name, User Email, Title, Description"
    model = models.Portfolio

    @admin.display(description='Tenant')
    def get_tenant(self, obj):
        return obj.tenant.name if obj.tenant else ''
    
    @admin.display(description='User')
    def get_user(self, obj):
        return obj.user.email if obj.user else ''


class ReportBaseTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'uuid', 'title', 'is_official', 'get_tenant', 'is_approved',
        'is_default', 'created_at', 'updated_at', 'category'
    )
    model = models.ReportBaseTemplate

    @admin.display(description='Tenant')
    def get_tenant(self, obj):
        return obj.tenant.name if obj.tenant else ''


class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name',)
    model = models.DataSource


class DataConnectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DataConnectionForm, self).__init__(*args, **kwargs)
        self.fields['data_source'] = forms.ChoiceField(
            choices=[(app.slug, app.name) for app in models.DataSource.objects.all()],
            widget=Select2Widget
        )

    class Meta:
        model = models.DataConnection
        fields = '__all__'


class DataConnectionAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'data_source', 'get_tenant')
    search_fields = ["tenant__name", "data_source"]
    list_filter = ["data_source", ("tenant__name", custom_titled_filter('Tenant Name')),]
    search_help_text = "Search by Tenant Name, DataSource"
    model = models.DataConnection
    change_form_template = 'admin/custom_change_form.html'
    form = DataConnectionForm

    @admin.display(description='Tenant')
    def get_tenant(self, obj):
        return obj.tenant.name if obj.tenant else ''
    
    def response_change(self, request, obj):
        if "_refresh_token" in request.POST:
            service = DataConnectionService(data_connection=obj)
            service.refresh_token()
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)


class ReleaseNoteAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'heading', 'created_at')
    model = models.ReleaseNote


admin.site.register(models.Tenant, TenantAdmin)
admin.site.register(models.StoryRoom, StoryRoomAdmin)
admin.site.register(models.Donation, DonationAdmin)
admin.site.register(models.Portfolio, PortfolioAdmin)
admin.site.register(models.ReportBaseTemplate, ReportBaseTemplateAdmin)
admin.site.register(models.DataSource, DataSourceAdmin)
admin.site.register(models.DataConnection, DataConnectionAdmin)
admin.site.register(models.ReleaseNote, ReleaseNoteAdmin)
