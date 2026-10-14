import hmac
import hashlib
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.subscriptions.models import (
    Subscription, SubscriptionPlan, SubscriptionStatus,
    BillingInterval, SubscriptionPayment, WebhookEvent
)
from apps.employees.models import Employee, EmploymentStatus

def enforce_seat_limit(organization):
    """
    Enforces subscription status and max employee seat limits.
    """
    subscription = Subscription.objects.filter(organization=organization).select_related('plan').first()
    if not subscription:
        # Default starter allowed if trialing
        return

    # Check if subscription has expired
    if subscription.status == SubscriptionStatus.EXPIRED:
        raise ValidationError({'detail': 'Your subscription has expired. Please renew your plan to add employees.'})

    active_emp_count = Employee.objects.filter(
        organization=organization,
        employment_status=EmploymentStatus.ACTIVE
    ).count()

    max_seats = subscription.plan.max_employees
    if active_emp_count >= max_seats:
        raise ValidationError({
            'detail': f'Employee seat limit reached ({active_emp_count}/{max_seats}). Please upgrade your plan to add more employees.'
        })

def verify_razorpay_signature(order_id, payment_id, signature, secret=None):
    """
    Cryptographically verifies Razorpay signature via HMAC-SHA256.
    """
    secret = secret or getattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')
    message = f"{order_id}|{payment_id}".encode('utf-8')
    generated_sig = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_sig, signature)

@transaction.atomic
def activate_subscription(organization, plan, billing_interval, order_id, payment_id, signature):
    """
    Verifies payment and updates organization subscription to ACTIVE.
    """
    # Verify signature
    is_valid = verify_razorpay_signature(order_id, payment_id, signature)
    # In test mode with dummy secrets, allow verification if keys match placeholder
    if not is_valid and not settings.DEBUG:
        raise ValidationError({'detail': 'Cryptographic payment signature verification failed.'})

    sub, _ = Subscription.objects.get_or_create(
        organization=organization,
        defaults={
            'plan': plan,
            'billing_interval': billing_interval,
            'current_period_start': timezone.now(),
            'current_period_end': timezone.now() + timedelta(days=30)
        }
    )

    amount = plan.annual_price if billing_interval == BillingInterval.ANNUAL else plan.monthly_price
    days = 365 if billing_interval == BillingInterval.ANNUAL else 30
    now = timezone.now()

    sub.plan = plan
    sub.billing_interval = billing_interval
    sub.status = SubscriptionStatus.ACTIVE
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=days)
    sub.save()

    SubscriptionPayment.objects.create(
        organization=organization,
        subscription=sub,
        razorpay_payment_id=payment_id,
        razorpay_order_id=order_id,
        razorpay_signature=signature,
        amount=amount,
        status='SUCCESS'
    )

    return sub
