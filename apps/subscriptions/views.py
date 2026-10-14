import uuid
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import IsTenantMember, IsOrganizationOwnerOrHR
from apps.employees.models import Employee, EmploymentStatus
from apps.subscriptions.models import (
    Subscription, SubscriptionPlan, SubscriptionStatus, WebhookEvent
)
from apps.subscriptions.serializers import (
    SubscriptionSerializer, SubscriptionPlanSerializer,
    CheckoutRequestSerializer, VerifyPaymentSerializer
)
from apps.subscriptions.services import activate_subscription, verify_razorpay_signature

class CurrentSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        sub = Subscription.objects.filter(organization=request.organization).select_related('plan').first()
        active_emp_count = Employee.objects.filter(
            organization=request.organization,
            employment_status=EmploymentStatus.ACTIVE
        ).count()

        if not sub:
            return Response({'error': {'message': 'No active subscription found.'}}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        days_left = max(0, (sub.current_period_end - now).days) if sub.current_period_end else 0

        data = SubscriptionSerializer(sub).data
        data['active_employees_count'] = active_emp_count
        data['seats_remaining'] = max(0, sub.plan.max_employees - active_emp_count)
        data['days_remaining'] = days_left
        data['is_trial'] = sub.status == SubscriptionStatus.TRIALING

        return Response(data)

class SubscriptionPlanListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('monthly_price')

class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plan = generics.get_object_or_404(SubscriptionPlan, code=data['plan_code'])
        amount = plan.annual_price if data['billing_interval'] == 'ANNUAL' else plan.monthly_price

        # In production, Razorpay client generates real order
        # For dev/sandbox, create deterministic order ID
        order_id = f"order_{uuid.uuid4().hex[:16]}"

        return Response({
            'success': True,
            'order_id': order_id,
            'amount': int(amount * 100), # in paise
            'currency': 'INR',
            'key_id': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_placeholder_key_id'),
            'plan_name': plan.name,
            'billing_interval': data['billing_interval']
        })

class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plan = generics.get_object_or_404(SubscriptionPlan, code=data['plan_code'])

        sub = activate_subscription(
            organization=request.organization,
            plan=plan,
            billing_interval=data['billing_interval'],
            order_id=data['razorpay_order_id'],
            payment_id=data['razorpay_payment_id'],
            signature=data['razorpay_signature']
        )

        return Response({
            'success': True,
            'message': f"Subscription to {plan.name} activated successfully.",
            'subscription': SubscriptionSerializer(sub).data
        })

class RazorpayWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        event_id = request.headers.get('X-Razorpay-Event-Id') or str(uuid.uuid4())
        
        # Check idempotency
        if WebhookEvent.objects.filter(event_id=event_id).exists():
            return Response({'status': 'ignored_duplicate'}, status=status.HTTP_200_OK)

        payload = request.data
        event_type = payload.get('event', 'unknown')

        WebhookEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            processed=True
        )

        return Response({'status': 'processed'}, status=status.HTTP_200_OK)
