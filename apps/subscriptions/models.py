from decimal import Decimal
from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class SubscriptionStatus(models.TextChoices):
    TRIALING = 'TRIALING', 'Trialing'
    ACTIVE = 'ACTIVE', 'Active'
    PAST_DUE = 'PAST_DUE', 'Past Due'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'

class BillingInterval(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    ANNUAL = 'ANNUAL', 'Annual'

class SubscriptionPlan(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=50) # Starter, Growth, Business, Enterprise
    code = models.CharField(max_length=50, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_employees = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['monthly_price']

    def __str__(self):
        return f"{self.name} (Up to {self.max_employees} employees)"

class Subscription(TenantScopedModel):
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    billing_interval = models.CharField(max_length=10, choices=BillingInterval.choices, default=BillingInterval.MONTHLY)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING, db_index=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField(db_index=True)
    razorpay_subscription_id = models.CharField(max_length=100, blank=True)
    razorpay_customer_id = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.status})"

class SubscriptionPayment(TenantScopedModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    razorpay_payment_id = models.CharField(max_length=100)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='SUCCESS')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment ₹{self.amount} ({self.status})"

class WebhookEvent(UUIDModel, TimeStampedModel):
    event_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Webhook {self.event_type} - {self.event_id}"
