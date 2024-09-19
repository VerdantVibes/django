from rest_framework import serializers

from django.core.exceptions import ValidationError

from core import models

def validate_mime_type(value):
    # mime = magic.Magic(mime=True)
    # mime_type = mime.from_buffer(value.read(1024))
    # allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    # if mime_type not in allowed_types:
    #     raise ValidationError('Invalid file format. Only JPG, PNG, and GIF files are allowed.')
    # value.seek(0)  # Reset file pointer for further processing
    pass

class UploadImageReportSerializer(serializers.Serializer):
  file = serializers.FileField(validators=[validate_mime_type])

class PortfolioSerializer(serializers.ModelSerializer):
    image_file_keys = serializers.ListField(
        child=serializers.CharField(),
        write_only=True
    )
    category_verbose = serializers.SerializerMethodField()

    class Meta:
        model = models.Portfolio
        fields = ['uuid', 'tenant', 'user', 'category', 'category_verbose',
                  'title', 'description', 'html_file_key', 'image_file_keys',
                  'report_id', 'created_at', 'updated_at']
        read_only_fields = ['tenant', 'user']

    def create(self, validated_data):
        validated_data.pop('image_file_keys', [])
        portfolio = models.Portfolio.objects.create(**validated_data)
        return portfolio

    def get_category_verbose(self, obj):
        category_mapping = dict(models.PORTFOLIO_CATEGORIES)
        return category_mapping.get(obj.category) or ''


class ReportBaseTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ReportBaseTemplate
        fields = [
            'uuid', 'title', 'description', 'template_file', 'is_approved',
            'is_official', 'is_default', 'created_at', 'updated_at', 'category'
        ]
        read_only_fields = ['categories', 'tenant']


class DataConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DataConnection
        fields = '__all__'


class StoryRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StoryRoom
        fields = '__all__'
        read_only_fields = ['uuid', 'categories', 'tenant']


class DonateSerializer(serializers.Serializer):
    mode = serializers.CharField(max_length=16)
    amount = serializers.IntegerField(min_value=1)
    donate_as = serializers.CharField(max_length=128)
    cover_fees = serializers.BooleanField()
    tenant_uuid = serializers.CharField(max_length=128)


class ReleaseNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ReleaseNote
        fields = '__all__'
