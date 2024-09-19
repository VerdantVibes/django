import uuid
import logging
import urllib.parse
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions

from core import serializers
from core import models
from core import utils

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class DonateView(APIView):
    """donate by Stripe"""
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None, *args, **kwargs):
        client_reference_id = str(uuid.uuid4())
        serializer = serializers.DonateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            # {'mode': 'payment', 'amount': 20, 'donate_as': 'individual', 'cover_fees': True, 'tenant_uuid': '123'}
            tenant_id = data['tenant_uuid']
            tenant = models.Tenant.objects.get(uuid=tenant_id)
            mode = data['mode']
            interval = None
            if mode == 'monthly':
                mode = 'subscription'
                interval = 'month'
            elif mode == 'annually':
                mode = 'subscription'
                interval = 'year'
            amount = data['amount']
            cover_fees = data['cover_fees']
            if cover_fees:
                amount = amount + amount * 0.05
            try:
                line_item = {
                    "price_data": {
                        "unit_amount": int(amount * 100),
                        "currency": "usd",
                        "product_data": {
                            "name": f"Donate ${amount}"
                        }
                    },
                    "quantity": 1,
                }
                if mode == 'subscription':
                    line_item["price_data"]["recurring"] = {
                        "interval": interval
                    }
                return_url_params = {
                    "tenant_name": tenant.name,
                    "tenant_website": tenant.website,
                    "tenant_support_email": tenant.support_email
                }
                session_data = {
                    'client_reference_id': client_reference_id,
                    'ui_mode': "embedded",
                    'line_items': [line_item],
                    'mode': mode,
                    'return_url': settings.FRONTEND_DOMAIN + '/donate/return?session_id={CHECKOUT_SESSION_ID}' + '&' + urllib.parse.urlencode(return_url_params),
                    'automatic_tax': {'enabled': True},
                    'metadata': {'tenant_name': tenant.name, 'tenant_uuid': tenant_id},
                }

                if mode == 'payment':
                    session_data['payment_intent_data'] = {
                        'metadata': {'tenant_name': tenant.name, 'tenant_uuid': tenant_id}
                    }

                session = stripe.checkout.Session.create(**session_data)

                models.Donation.objects.create(
                    uuid=client_reference_id,
                    mode=mode,
                    amount=data['amount'],
                    donate_as=data['donate_as'],
                    cover_fees=cover_fees,
                    status='init',
                    tenant_id=data['tenant_uuid']
                )
                return Response(status=status.HTTP_200_OK, data={"clientSecret": session.client_secret})
            except Exception as e:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data=str(e))
        return Response(status=status.HTTP_400_BAD_REQUEST)


class DonateReturnView(APIView):
    """donate return by Stripe"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None, *args, **kwargs):
        session = stripe.checkout.Session.retrieve(request.query_params.get('session_id'))
        return Response(status=status.HTTP_200_OK, data=session)


class DonateCancelView(APIView):
    """cancel recurring donation"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None, *args, **kwargs):
        subscription_id = request.query_params.get('subscription_id')
        result = stripe.Subscription.cancel(subscription_id)
        donation = models.Donation.objects.get(subscription=subscription_id)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': result.status,
                'tenant_name': donation.tenant.name,
                'tenant_website': donation.tenant.website
            })


@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.info('Stripe Webhook: Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.info('Stripe Webhook: Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    logger.info(str(event))
    
    if event.type == 'checkout.session.completed':  # one-time/recurring paid
        client_reference_id = event['data']['object']['client_reference_id']
        status = event['data']['object']['status']
        subscription = event['data']['object']['subscription']
        customer_email = event['data']['object']['customer_details']['email']
        models.Donation.objects.filter(uuid=client_reference_id).update(status=status, subscription=subscription)
        if subscription:
            try:
                tenant = models.Donation.objects.get(uuid=client_reference_id).tenant
                utils.send_cancellation_email(subscription_id=subscription, customer_email=customer_email, tenant_name=tenant.name)
            except Exception as ex:
                logger.info(f'send cancellation email failed: {ex}')

            stripe.Subscription.modify(
                subscription,
                metadata=event['data']['object']['metadata']
            )
    elif event.type == 'invoice.payment_succeeded':  # for successful subscription payments
        status = event['data']['object']['status']
        subscription = event['data']['object']['subscription']
        if subscription:
            models.Donation.objects.filter(subscription=subscription).update(status=status)
    elif event.type == 'customer.subscription.deleted':  # for for subscription cancellations
        status = event['data']['object']['status']
        subscription = event['data']['object']['id']
        if subscription:
            models.Donation.objects.filter(subscription=subscription).update(status=status)
    elif event.type == 'invoice.payment_failed':  # for failed subscription payments
        status = event['data']['object']['status']  # `open`
        subscription = event['data']['object']['subscription']
        if subscription:
            models.Donation.objects.filter(subscription=subscription).update(status=status)
    else:
        logger.info('Stripe Webhook: ignored event type {}'.format(event.type))

    return HttpResponse(status=200)
