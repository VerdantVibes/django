import logging
from django.conf import settings
from bs4 import BeautifulSoup

from azure.communication.email import EmailClient

logger = logging.getLogger(__name__)


def extract_title(content):
    if not content:
        return "Untitled Report"
    soup = BeautifulSoup(content, 'html.parser')
    h1 = soup.find('h1')
    return h1.text if h1 else "Untitled Report"


def send_cancellation_email(subscription_id, customer_email, tenant_name):
    """email user the cancellation url link"""
    connection_string = settings.AZURE_COMMUNICATION_CONNECTION_STRING

    try:
        connection_string = connection_string
        client = EmailClient.from_connection_string(connection_string)


        subject = f"Thank You for Your Recurring Donation to {tenant_name}"
        cancellation_url = f"https://app.getcadenza.com/donate/cancel/{subscription_id}"
        body = f"To cancel your recurring donation, please click the following link: {cancellation_url}"
        html_body = f"To cancel your recurring donation, please click the following link: <a href='{cancellation_url}'>{cancellation_url}</a>"

        message = {
            "senderAddress": "DoNotReply@getcadenza.com",
            "recipients":  {
                "to": [{"address": customer_email }],
            },
            "content": {
                "subject": subject,
                "plainText": body,
                "html": f"<html><h1>{subject}</h1><p>{html_body}</p></html>"
            }
        }

        poller = client.begin_send(message)
        result = poller.result()
        logger.info(f"send email result: {result}")

    except Exception as ex:
        logger.info(f"Failed to send email: {ex}")


def send_email(customer_email, subject, content):
    """email user, e.g. send reset password link"""
    connection_string = settings.AZURE_COMMUNICATION_CONNECTION_STRING

    try:
        connection_string = connection_string
        client = EmailClient.from_connection_string(connection_string)

        body = content
        html_body = content

        message = {
            "senderAddress": "DoNotReply@getcadenza.com",
            "recipients":  {
                "to": [{"address": customer_email }],
            },
            "content": {
                "subject": subject,
                "plainText": body,
                "html": f"<html><h1>{subject}</h1><p>{html_body}</p></html>"
            }
        }

        poller = client.begin_send(message)
        result = poller.result()
        logger.info(f"send email result: {result}")

    except Exception as ex:
        logger.info(f"Failed to send email: {ex}")
