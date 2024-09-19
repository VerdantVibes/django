import logging
import requests

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions

logger = logging.getLogger(__name__)


class FeedbackView(APIView):
    """send feedback to Slack"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None, *args, **kwargs):
        user = request.user
        tenant = user.tenant
        data = request.data
        webhook_url = settings.SLACK_WEBHOOK_URL
        text = f'user {user}, from {tenant},\nFEEDBACK: {data.get("message")}'
        if data.get('reportId'):
            text += f',\nDETAILS: https://langfuse.getcadenza.com/project/clyh2ord90001sb1bp5yctmku/traces?filter=metadata%3BstringObject%3BreportID%3B%3D%3B{data.get("reportId")}'
        elif data.get('chatId'):
            text += f',\nDETAILS: https://langfuse.getcadenza.com/project/clyh2ord90001sb1bp5yctmku/traces?filter=metadata%3BstringObject%3BsessionID%3B%3D%3B{data.get("chatId")}'
        
        message = {
            'text': text
        }
        response = requests.post(webhook_url, json=message)
        if response.status_code != 200:
            logger.error(response.content)
            return Response("error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response("ok", status=status.HTTP_200_OK)
