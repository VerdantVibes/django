import re
import datetime
import io
import logging
from datetime import timedelta

import requests
from urllib.parse import quote
from django.conf import settings
from django.http import HttpResponse
from django.template import Context, Template
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django.urls import reverse
from django.http import Http404
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from azure.storage.blob import BlobClient, BlobServiceClient
from bs4 import BeautifulSoup
from exa_py import Exa

from core import models
from core import serializers
from core.services import DataConnectionService
from authentication.permissions import TenantAdminPermission

logger = logging.getLogger(__name__)


class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = models.Portfolio.objects.all()
    serializer_class = serializers.PortfolioSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category']
    search_fields = ['title', 'description']

    def get_object(self):
        instance = super().get_object()
        user = self.request.user
        if instance.user == user:
            return instance
        else:
            raise Http404

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        qs = qs.filter(user=user).order_by('-created_at')
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        tenant = user.tenant
        html_file_key = serializer.validated_data['html_file_key']
        self.copy_blob(html_file_key)

        image_file_keys = serializer.validated_data.get('image_file_keys', [])
        for image_file_key in image_file_keys:
            self.copy_blob(image_file_key)

        category = serializer.validated_data['category']
        title = self.get_html_title(html_file_key, category)

        serializer.save(user=user, tenant=tenant, title=title)

    def copy_blob(self, blob_key):
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        source_blob = blob_service_client.get_blob_client(container=settings.AZURE_STORAGE_CHAT_BOT_CONTAINER_NAME, blob=blob_key)
        target_blob = blob_service_client.get_blob_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME, blob=blob_key)
        target_blob.start_copy_from_url(source_blob.url)

    def get_html_title(self, blob_key, category):
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=settings.AZURE_STORAGE_CHAT_BOT_CONTAINER_NAME, blob=blob_key)

        blob_data = blob_client.download_blob()
        html_content = blob_data.readall()

        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('h4')

        current_time = timezone.localtime()
        formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")

        return title_tag.get_text() if title_tag else f'Data{category}_{formatted_time}'

    def perform_destroy(self, instance):
        blob_key = instance.html_file_key
        if instance.category == "impactReport":
            blob_key = instance.report_id + "/"
        self.delete_blob_and_directory_contents(blob_key)
        instance.delete()

    def delete_blob_and_directory_contents(self, blob_key):
        directory_path = '/'.join(blob_key.split('/')[:-1])

        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        container = blob_service_client.get_container_client(settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)

        for blob in container.list_blobs(name_starts_with=directory_path):
            blob_client = container.get_blob_client(blob)
            blob_client.delete_blob()

    @action(detail=True)
    def download(self, request, pk=None):
        is_impact_report = request.query_params.get('isImpactReport', None)
        file_type = request.query_params.get('fileType', None)
        portfolio = self.get_object()
        html_file_key = portfolio.html_file_key

        if is_impact_report == 'true' and file_type == 'PDF':
            report_url = request.build_absolute_uri(f"{reverse('fetch-report-as-html')}?report_id={portfolio.report_id}")
            pdf_content = self.get_impact_pdf(report_url, portfolio.report_id)
            if pdf_content:
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="report.pdf"'
                response.write(pdf_content)
                return response
        elif is_impact_report == 'true' and file_type == 'DOC':
            report_url = request.build_absolute_uri(f"{reverse('fetch-report-as-html')}?report_id={portfolio.report_id}")
            doc_content = self.get_impact_doc(report_url, portfolio.report_id)
            if doc_content:
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = 'attachment; filename="report.docx"'
                response.write(doc_content)
                return response
        
        if file_type == 'PDF':
            pdf_content = self.get_pdf(html_file_key, portfolio.category)
            if pdf_content:
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="report.pdf"'
                response.write(pdf_content)
                return response
        elif file_type == 'PPT':
            ppt_content = self.get_ppt(html_file_key, portfolio.category)
            if ppt_content:
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
                response['Content-Disposition'] = 'attachment; filename="report.ppt"'
                response.write(ppt_content)
                return response
        elif file_type == 'DOC':
            doc_content = self.get_doc(html_file_key, portfolio.category)
            if doc_content:
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = 'attachment; filename="report.docx"'
                response.write(doc_content)
                return response
        else:
            return Response({'message': 'No report content found'}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_impact_pdf(self, report_url, report_id):
        pdf_file_key = f"{report_id}/{report_id}.pdf"
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME,
            blob=pdf_file_key)

        if blob_client.exists():
            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            return blob_content
        else:
            pdf_url = f"{settings.PDF_FUNC_DOMAIN}/api/convert-html-to-pdf?url={report_url}"
            response = requests.get(pdf_url)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception("Failed to retrieve data from the converter")
    
    def get_impact_doc(self, report_url, report_id):
        self.get_impact_pdf(report_url, report_id)  # make sure PDF file exists

        doc_file_key = f"{report_id}/{report_id}.docx"
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME,
            blob=doc_file_key)

        if blob_client.exists():
            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            return blob_content
        else:
            path_name = report_id
            html_name = f"{report_id}.html"
            doc_url = f"{settings.DOC_FUNC_DOMAIN}&path_name={path_name}&html_name={html_name}"
            response = requests.get(doc_url)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception("Failed to retrieve data from the converter")


    def get_pdf(self, html_file_key, category):
        pdf_file_key = html_file_key.replace('.html', '.pdf')
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME,
            blob=pdf_file_key)

        if blob_client.exists():
            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            return blob_content
        else:
            original_url = f"{settings.API_DOMAIN}/api/core/download/{html_file_key}/?show_html=true&category={category}&is_portfolio_page=true&user_id={self.request.user.id}"
            escaped_url = quote(original_url, safe='')
            pdf_url = f"{settings.PDF_FUNC_DOMAIN}/api/convert-html-to-pdf?url={escaped_url}"
            response = requests.get(pdf_url)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception("Failed to retrieve data from the converter")
    
    def get_ppt(self, html_file_key, category):
        ppt_file_key = html_file_key.replace('.html', '.pptx')
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME,
            blob=ppt_file_key)

        if blob_client.exists():
            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            return blob_content
        else:
            # NOTE: official template don't use is_approved field, MUST CONTAIN THE CATEGORY
            default_template = models.ReportBaseTemplate.objects.get(title__icontains=category, is_official=True, category='PPT')
            template_file = default_template.template_file.url.split('/')[-1]

            user = self.request.user
            tenant = user.tenant
            template_of_tenant = models.ReportBaseTemplate.objects.filter(tenant=tenant, is_approved=True, is_default=True, category='PPT').first()
            if template_of_tenant:
                template_file = template_of_tenant.template_file.url.split('/')[-1]

            file_key_group = html_file_key.split('/')
            path_name = file_key_group[0]
            html_name = file_key_group[1]
            ppt_url = f"{settings.PPT_FUNC_DOMAIN}&path_name={path_name}&html_name={html_name}&template_file={template_file}"
            response = requests.get(ppt_url)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception("Failed to retrieve data from the converter")
    
    def get_doc(self, html_file_key, category):
        self.get_pdf(html_file_key, category)  # make sure PDF file exists

        doc_file_key = html_file_key.replace('.html', '.docx')
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME,
            blob=doc_file_key)

        if blob_client.exists():
            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            return blob_content
        else:
            file_key_group = html_file_key.split('/')
            path_name = file_key_group[0]
            html_name = file_key_group[1]
            doc_url = f"{settings.DOC_FUNC_DOMAIN}&path_name={path_name}&html_name={html_name}"
            response = requests.get(doc_url)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception("Failed to retrieve data from the converter")
    
    @action(detail=False)
    def latest(self, request):
        user = self.request.user
        category = request.query_params.get('category', None)

        query = models.Portfolio.objects.filter(user=user).order_by('-created_at')

        if category:
            query = query.filter(category=category)

        latest_portfolios = query[:3]
        serializer = self.get_serializer(latest_portfolios, many=True)
        return Response(serializer.data)


def create_replace_function(blob_name, is_portfolio_page):
    def replace_src(match):
        image_name = match.group(1)
        if is_portfolio_page:
            return f'<img src="{settings.API_DOMAIN}/api/core/download/{blob_name}/{image_name}/?show_image=true&is_portfolio_page=true"'
        return f'<img src="{settings.API_DOMAIN}/api/core/download/{blob_name}/{image_name}/?show_image=true"'
    return replace_src


@method_decorator(xframe_options_exempt, name='dispatch')
class DownloadView(APIView):
    """ User can retrieve specific files (image or HTML) from Azure Blob Storage 
     - **it have to be AZURE_STORAGE_CHAT_BOT_CONTAINER_NAME, because before `save to portfolio`,
       the blob does not exist in AZURE_STORAGE_REPORT_CONTAINER_NAME**
    """
    def get(self, request, *args, **kwargs):
        file_name = kwargs['name']
        show_image = request.query_params.get('show_image')
        show_document = request.query_params.get('show_document')  # CZ-125 download document from `customerdatasources`
        show_html = request.query_params.get('show_html')
        category = request.query_params.get('category') or 'story'
        is_portfolio_page = request.query_params.get('is_portfolio_page')
        blob_name = f"{kwargs['blob']}/{file_name}"
        
        container_name = settings.AZURE_STORAGE_CHAT_BOT_CONTAINER_NAME
        if is_portfolio_page:
            container_name = settings.AZURE_STORAGE_REPORT_CONTAINER_NAME
        
        if show_document:
            container_name = settings.AZURE_STORAGE_RAG_CONTAINER_NAME
            blob_client = BlobClient.from_connection_string(
                conn_str=settings.AZURE_STORAGE_RAG_CONNECTION_STRING,
                container_name=container_name,
                blob_name=blob_name)
        else:
            blob_client = BlobClient.from_connection_string(
                conn_str=settings.AZURE_STORAGE_CONNECTION_STRING,
                container_name=container_name,
                blob_name=blob_name)
        
        try:
            blob_data = blob_client.download_blob()
            content_type = blob_client.get_blob_properties().content_settings.content_type
            blob_content = blob_data.readall()

            if show_image:
                response = HttpResponse(blob_content, content_type="image/png", status=status.HTTP_200_OK)
            elif show_html:
                blob_content = blob_content.decode("utf-8")
                pattern = r'<img src=["\'](?:file://)?([^"\']+?)["\']'
                blob_content = re.sub(pattern, create_replace_function(kwargs['blob'], is_portfolio_page), blob_content)
                base_html_template = self.get_base_html_template(category)
                template = Template(base_html_template)
                context = Context({'blob_content': blob_content})
                return HttpResponse(template.render(context))
            else:
                response = HttpResponse(blob_content, content_type=content_type, status=status.HTTP_200_OK)
                response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}", status=status.HTTP_404_NOT_FOUND)

    def get_base_html_template(self, category):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            UserModel = get_user_model()
            user = UserModel.objects.get(id=user_id)
        else:
            user = self.request.user
        tenant = user.tenant

        container_name = settings.AZURE_STORAGE_MEDIA_CONTAINER_NAME
        blob_name = None

        template_of_tenant = models.ReportBaseTemplate.objects.filter(tenant=tenant, is_approved=True, is_default=True, category='PDF').first()
        if template_of_tenant:
            blob_name = template_of_tenant.template_file.url.split('/')[-1]
            blob_name = f'base_report_template/{blob_name}'
        else:
            template = models.ReportBaseTemplate.objects.get(is_official=True, category='PDF', title__icontains=category)
            blob_name = template.template_file.url.split('/')[-1]
            blob_name = f'base_report_template/{blob_name}'

        blob_client = BlobClient.from_connection_string(
            conn_str=settings.AZURE_STORAGE_CONNECTION_STRING,
            container_name=container_name,
            blob_name=blob_name)
        blob_data = blob_client.download_blob()
        blob_content = blob_data.readall()
        return blob_content.decode("utf-8")


class ReportBaseTemplateViewSet(viewsets.ModelViewSet):
    queryset = models.ReportBaseTemplate.objects.all()
    serializer_class = serializers.ReportBaseTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        instance = super().get_object()
        user = self.request.user
        if instance.tenant == user.tenant:
            return instance
        else:
            raise Http404

    def get_queryset(self):
        category = self.request.query_params.get('category') or 'PDF'
        user = self.request.user
        qs = super().get_queryset()
        custom_default_exists = qs.filter(tenant=user.tenant, is_default=True, category=category).exists()
        qs = qs.filter(Q(tenant=user.tenant) | Q(is_official=True), category=category).order_by('-is_official', '-created_at')
        if not custom_default_exists:
            for instance in qs:
                if instance.is_official:
                    instance.is_default = True
                    break
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        tenant = user.tenant
        serializer.save(tenant=tenant)
    
    def perform_destroy(self, instance):
        if not instance.is_official:
            instance.delete()

    @action(detail=True, methods=['post'])
    def set_as_default(self, request, pk=None):
        category = request.query_params.get('category') or 'PDF'
        user = self.request.user
        qs = super().get_queryset()
        qs.filter(tenant=user.tenant, category=category).update(is_default=False)
        instance = self.get_object()
        instance.is_default = True
        instance.save()
        return Response(status=status.HTTP_200_OK)


class DataConnectionListView(generics.ListAPIView):
    queryset = models.DataConnection.objects.all()
    serializer_class = serializers.DataConnectionSerializer
    permission_classes = [TenantAdminPermission]


class DataConnectionRefreshTokenView(APIView):
    """refresh token of data connection"""
    permission_classes = [TenantAdminPermission]

    def get(self, request, format=None, *args, **kwargs):
        data_connection_uuid = kwargs['data_connection_uuid']
        service = DataConnectionService(data_connection_uuid=data_connection_uuid)
        service.refresh_token()

        data_connection = models.DataConnection.objects.get(uuid=data_connection_uuid)
        serializer = serializers.DataConnectionSerializer(data_connection)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class DataConnectionFoldersView(APIView):
    """CZ-114, get selected folders"""
    permission_classes = [TenantAdminPermission]

    def get(self, request, format=None, *args, **kwargs):
        data_connection_uuid = kwargs['data_connection_uuid']

        data_connection = models.DataConnection.objects.get(uuid=data_connection_uuid)
        serializer = serializers.DataConnectionSerializer(data_connection)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class StoryRoomViewSet(viewsets.ModelViewSet):
    queryset = models.StoryRoom.objects.all()
    serializer_class = serializers.StoryRoomSerializer
    permission_classes = [TenantAdminPermission]
    pagination_class = None

    def get_object(self):
        instance = super().get_object()
        user = self.request.user
        if instance.tenant == user.tenant:
            return instance
        else:
            raise Http404

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        qs = qs.filter(tenant=user.tenant)
        
        if not qs:
            tenant = user.tenant
            models.StoryRoom.objects.create(enabled=False, tenant=tenant)
            qs = qs.filter(tenant=user.tenant)

        return qs


class StoryRoomVerify(APIView):
    """CZ-107, ananymous verify by `Tenant Name` before they can upload story"""
    permission_classes = []

    def post(self, request, *args, **kwargs):
        tenant_name = request.data.get('tenant_name')
        error_message = 'Unrecognized Story Room'

        try:
            tenant = models.Tenant.objects.get(name__iexact=tenant_name)
        except models.Tenant.DoesNotExist:
            return Response({'error': error_message}, status=status.HTTP_404_NOT_FOUND)
        try:
            story_room_instance = models.StoryRoom.objects.get(tenant=tenant, enabled=True)
        except models.StoryRoom.DoesNotExist:
            return Response({'error': error_message}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'tenant_uuid': tenant.uuid,
            'logo': tenant.logo.url if tenant.logo else None,
            'categories': story_room_instance.categories,
            'allow_donation': story_room_instance.allow_donation
        }
        return Response(data, status=status.HTTP_200_OK)


def sanitize_metadata_value(value):
    return ''.join(char for char in value if ord(char) < 128)


class StoryRoomUpload(APIView):
    """CZ-107, upload story"""
    permission_classes = []

    @staticmethod
    def recaptcha(request_data):
        data = {
            'response': request_data.get('token'),
            'secret': settings.RECAPTCHA_V3_SECRET_KEY
        }
        resp = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result_json = resp.json()
        return result_json

    def post(self, request, *args, **kwargs):
        recaptcha_result = self.recaptcha(request.data)

        logger.info(f"recaptcha v3 result: {recaptcha_result}")
        if not recaptcha_result.get('success') or recaptcha_result.get('action') != 'story_room' or recaptcha_result.get('score') < 0.5:
            return Response('bad request', status=status.HTTP_403_FORBIDDEN)

        tenant_uuid = request.data.get('tenant_uuid')
        name = request.data.get('name')
        category = request.data.get('category')
        story = request.data.get('story')

        current = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = sanitize_metadata_value(f"{name}-{category}-{current}.txt")

        metadata = {
            'Created_By_Display_Name': name,
            'Created_At': current,
            'Last_Modified_By_Display_Name': name,
            'Last_Modified_At': current,
            'Category': category,
            'Summary': sanitize_metadata_value(story[:128])
        }

        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_RAG_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_RAG_CONTAINER_NAME)
        text = f"""
            StoryRoom Feedback: {category}
            Name: {name}

            Date: {current}
            Story: {story}
        """
        data = io.BytesIO(text.encode('utf-8'))
        container_client.upload_blob(name=f"{tenant_uuid}/storyRoom/{filename}", data=data, overwrite=True, metadata=metadata)

        return Response('ok', status=status.HTTP_200_OK)


class StoryList(APIView):
    """CZ-138, list stories of a tenant"""
    permission_classes = [TenantAdminPermission]

    def get(self, request, *args, **kwargs):
        user = request.user
        tenant_uuid = user.tenant.uuid

        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_RAG_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            container=settings.AZURE_STORAGE_RAG_CONTAINER_NAME
        )

        continuation_token = request.query_params.get('continuation_token') or None
        blob_list = container_client.list_blobs(
            name_starts_with=f"{tenant_uuid}/storyRoom/",
            include=['metadata'],
            results_per_page=100
        )
        blobs = blob_list.by_page(continuation_token)
        response_data = []
        current_page = blobs.next()
        for blob in current_page:
            response_data.append({
                'file_name': blob['name'],
                'etag': blob['etag'],
                'created_by': blob['metadata'].get('Created_By_Display_Name'),
                'created_at': blob['metadata'].get('Created_At'),
                'category': blob['metadata'].get('Category'),
                'summary': blob['metadata'].get('Summary'),
            })

        return Response({
            'blobs': response_data,
            'continuation_token': blobs.continuation_token
        }, status=status.HTTP_200_OK)


class Story(APIView):
    """CZ-138, delete story blob of a tenant by name"""
    permission_classes = [TenantAdminPermission]

    @staticmethod
    def _get_blob_client(file_name):
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_RAG_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            container=settings.AZURE_STORAGE_RAG_CONTAINER_NAME
        )
        blob_client = container_client.get_blob_client(blob=file_name)
        return blob_client

    def get(self, request, *args, **kwargs):
        file_name = request.query_params.get('fileName', None)
        if file_name:
            blob_client = self._get_blob_client(file_name)
            blob_data = blob_client.download_blob().readall()
            text_content = blob_data.decode('utf-8')
        else:
            text_content = ""
        return Response(text_content, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        file_name = request.data.get('file_name')
        blob_client = self._get_blob_client(file_name)
        blob_client.delete_blob()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReleaseNoteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.ReleaseNote.objects.all()
    serializer_class = serializers.ReleaseNoteSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.order_by('-created_at')[:4]
        return qs


class NewsFeedView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get_news(tenant_uuid, location, topics):
        cached_news = cache.get(f'news_feed_{tenant_uuid}')
        if cached_news:
            return cached_news
        exa = Exa(api_key=settings.EXA_API_KEY)

        current_time = timezone.localtime()
        threeweeks_ago = current_time - timedelta(days=21)
        prompt = f"Here is the top news and academic research for nonprofit organizations in {location} related to {topics}"

        resp = exa.search_and_contents(
            prompt,
            type="neural",
            use_autoprompt=True,
            category="research paper",
            num_results=10,
            start_published_date=threeweeks_ago.isoformat(),
            end_published_date=current_time.isoformat(),
            exclude_domains=["x.com", "youtube.com", "en.wikipedia.org", "twitter.com", "surveymonkey.com", "drive.google.com", "onedrive.live.com", "accounts.google.com", "mail.google.com", "login.microsoftonline.com", "bing.com"],
            highlights={ "numSentences": 2, "highlightsPerUrl": 4, "query":topics},
            summary=True
        )
        results = resp.results
        cache.set(f'news_feed_{tenant_uuid}', results, 24 * 60 * 60)

        return results

    def get(self, request, *args, **kwargs):
        user = request.user
        tenant_uuid = user.tenant.uuid
        primary_location = user.tenant.primary_location
        news_topics = user.tenant.news_topics
        try:
            news = self.get_news(tenant_uuid, location=primary_location, topics=news_topics)
            news = [{
                "score": n.score,
                "title": n.title,
                "id": n.id,
                "url": n.url,
                "published_date": n.published_date,
                "author": n.author,
                "text": n.text,
                "highlights": n.highlights,
                "summary": n.summary
            } for n in news]
            return Response(status=status.HTTP_200_OK, data=news)
        except Exception as e:
            logger.error(f"retrieve news from Exa failed: {e}")
            return Response(status=status.HTTP_200_OK, data=[])
