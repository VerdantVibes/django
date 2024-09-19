import io
import os
import datetime
import logging
import re
import json
import requests
import time
from core import utils

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.core.files.storage import FileSystemStorage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from azure.storage.blob import BlobServiceClient
from rest_framework import status

from core import models
from core import serializers

logger = logging.getLogger(__name__)


def sanitize_metadata_value(value):
    return ''.join(char for char in value if ord(char) < 128)


class UploadReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        tenant_uuid = user.tenant.uuid
        report_id = request.data.get('report_id')
        report_content = request.data.get('report_content')
        report_citations = request.data.get('report_citations', [])
        research_chunks = request.data.get('research_chunks', [])
        # Extract the title from the report content
        report_title = utils.extract_title(report_content)


        # Sanitize metadata values
        report_id = sanitize_metadata_value(report_id)
        report_title = sanitize_metadata_value(report_title)

        reportExist = models.Portfolio.objects.filter(
            report_id=report_id,
            tenant_id=tenant_uuid,
            user=user,
            category='impactReport',
        ).exists()

        if reportExist is True:
            instance = models.Portfolio.objects.filter(
                report_id=report_id,
                tenant_id=tenant_uuid,
                user=user,
                category='impactReport',
            ).first() 
        else:
            instance = models.Portfolio.objects.create(
                report_id=report_id,
                tenant_id=tenant_uuid,
                user=user,
                category='impactReport',
                title=report_title
            )


        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{report_id}/{report_id}.json"
        
        metadata = {
            'Report_ID': report_id,
            'Report_Title': report_title,
            'Created_By_User': user.username,
            'Created_At': current_time,
            'Last_Modified_At': current_time
        }

        text = json.dumps({
            'report_content': report_content,
            'report_citations': report_citations,
            'research_chunks': research_chunks
        })
        data = io.BytesIO(text.encode('utf-8'))

        try:
            blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)
            container_client.upload_blob(name=filename, data=data, overwrite=True, metadata=metadata)

            instance.title = report_title
            instance.save()

            return Response({'message': 'Report uploaded successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to upload report: {e}")
            return Response(f"Error: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FetchReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        report_id = request.query_params.get('report_id')
        file_name = f"{report_id}/{report_id}.json"

        try:
            blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)
            blob_client = container_client.get_blob_client(blob=file_name)

            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            content = json.loads(blob_content.decode('utf-8'))

            report_content = content['report_content']
            report_citations = content['report_citations']
            research_chunks = content['research_chunks']

            # Extract the title from the report content
            report_title = utils.extract_title(report_content)

            return JsonResponse({
                'report_id': report_id,
                'report_title': report_title,
                'report_content': report_content,
                'report_citations': report_citations,
                'research_chunks': research_chunks
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to fetch report: {e}")
            return Response(f"Error: {str(e)}", status=status.HTTP_404_NOT_FOUND)

class FetchReportImageView(APIView):
    def get(self, request, *args, **kwargs):
        image_key = request.query_params.get('image_key')
        if not (image_key):
            return Response({"message": "Report not exist."}, status=status.HTTP_404_NOT_FOUND)
        image_key = sanitize_metadata_value(image_key)
        report_id = re.split(r'/', image_key)[0]
        image_file = re.split(r'/', image_key)[1]

        try:
            # Find image exist in directory
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, f'portfolio_assets'))
            directory_path = fs.path(report_id)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            file_path = fs.path(image_key)

            if not os.path.exists(file_path):
                try:
                    # Else download from azure
                    blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
                    container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)
                    blob_client = container_client.get_blob_client(blob=image_key)

                    blob_data = blob_client.download_blob().readall()
                    
                    with open(file_path, 'wb') as f:
                        f.write(blob_data)
                except Exception as e:
                    logger.error(f"Failed to fetch image: {e}")
                    return Response(f"Error: {str(e)}", status=status.HTTP_404_NOT_FOUND)
                    
            if not os.path.exists(file_path):
                return Response({"message": "Not found."}, status=status.HTTP_404_NOT_FOUND)

            # Open the file for reading
            # mime = magic.Magic(mime=True)
            # content_type = mime.from_file(file_path)
            content_type = 'image/jpeg'

            with open(file_path, 'rb') as file:
                file_data = file.read()

            # Create a DRF Response object with file content
            response = HttpResponse(file_data, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{image_file}"'
            return response

        except Exception as e:
            logger.error(f"Failed to fetch report: {e}")
            return Response(f"Error: {str(e)}", status=status.HTTP_404_NOT_FOUND)

class UploadReportImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        tenant_uuid = user.tenant.uuid

        report_id = request.query_params.get('report_id')
        if not (report_id):
            return Response({"message": "Report not exist."}, status=status.HTTP_404_NOT_FOUND)
        report_id = sanitize_metadata_value(report_id)

        # Check Report ID exist
        instance = models.Portfolio.objects.filter(
            report_id=report_id,
            tenant_id=tenant_uuid,
            user=user,
            category='impactReport',
        ).first()

        if not (instance):
            return Response({"message": "Report not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Senitize File
        serializer = serializers.UploadImageReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']
        # Upload File
        # Save details to Portfolio assets

        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, f'portfolio_assets/{report_id}'))
        filename = fs.save(uploaded_file.name, uploaded_file)
        # uploaded_file_path = fs.path(filename)
        
        # Upload image to Azure
        try:
            blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)
            uploaded_file.seek(0)
            data = uploaded_file.read()
            _filename = f"{report_id}/{filename}"
            container_client.upload_blob(name=_filename, data=data, overwrite=True)

            # Get public url
            return Response({'message': "Upload Successfully.", "data": _filename }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to upload report: {e}")
            return Response(f"Error: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SaveReportImageFromUrlView(APIView):

    def post(self, request, *args, **kwargs):
        # user = request.user
        # tenant_uuid = user.tenant.uuid

        report_id = request.query_params.get('report_id')
        if not (report_id):
            return Response({"message": "Report not exist."}, status=status.HTTP_404_NOT_FOUND)
        report_id = sanitize_metadata_value(report_id)

        # Check Report ID exist
        instance = models.Portfolio.objects.filter(
            report_id=report_id,
            # tenant_id=tenant_uuid,
            # user=user,
            category='impactReport',
        ).first()

        if not (instance):
            return Response({"message": "Report not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Senitize File
        image_url = request.POST.get('image_url')
        if not image_url:
            return Response({'error': 'URL is required'}, status=400)

        # Fetch the content from the URL
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

         # Check MIME type from response headers
        content_type = response.headers.get('Content-Type')
        # Check content type is allowed
        if not content_type or not content_type.startswith('image/'):
            return Response({'error': 'The URL does not point to an image'}, status=400)

        # Get extension for content type
        file_extension = content_type.split('/')[1]  # e.g., 'jpeg' from 'image/jpeg'
        # Generate a file name and save the image
        filename = f'image_{int(time.time())}.{file_extension}'

        # Save file to directory with new name
        # Upload File
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, f'portfolio_assets/{report_id}'))
        filename = fs.save(filename, ContentFile(response.content))
        
        # Upload image to Azure
        try:
            blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)
            uploaded_file = ContentFile(response.content)
            uploaded_file.seek(0)
            data = uploaded_file.read()
            _filename = f"{report_id}/{filename}"
            container_client.upload_blob(name=_filename, data=data, overwrite=True)

            # Get public url
            return Response({'message': "Upload Successfully.", "data": _filename }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to upload report: {e}")
            return Response(f"Error: {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        tenant_uuid = user.tenant.uuid
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)

        continuation_token = request.query_params.get('continuation_token') or None
        blob_list = container_client.list_blobs(
            name_starts_with=f"{tenant_uuid}/",
            include=['metadata'],
            results_per_page=100
        )
        blobs = blob_list.by_page(continuation_token)
        response_data = []
        current_page = next(blobs)
        for blob in current_page:
            response_data.append({
                'file_name': blob.name,
                'etag': blob.etag,
                'report_id': blob.metadata.get('Report_ID'),
                'report_title': blob.metadata.get('Report_Title'),
                'created_at': blob.metadata.get('Created_At'),
                'last_modified_at': blob.metadata.get('Last_Modified_At'),
                'created_by': blob.metadata.get('Created_By_User'),
            })

        return Response({
            'reports': response_data,
            'continuation_token': blobs.continuation_token
        }, status=status.HTTP_200_OK)


class FetchReportAsHtmlView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        report_id = request.query_params.get('report_id')
        file_name = f"{report_id}/{report_id}.json"

        try:
            blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(container=settings.AZURE_STORAGE_REPORT_CONTAINER_NAME)
            blob_client = container_client.get_blob_client(blob=file_name)

            blob_data = blob_client.download_blob()
            blob_content = blob_data.readall()
            content = json.loads(blob_content.decode('utf-8'))

            report_content = content['report_content']

            return HttpResponse(report_content)
        except Exception as e:
            logger.error(f"Failed to fetch html report: {e}")
            return HttpResponse(f"Error: {str(e)}")