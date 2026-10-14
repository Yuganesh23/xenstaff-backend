from django.urls import path
from apps.subscriptions.views import (
    CurrentSubscriptionView, SubscriptionPlanListView,
    CheckoutView, VerifyPaymentView, RazorpayWebhookView
)

urlpatterns = [
    path('current', CurrentSubscriptionView.as_view(), name='subscription-current'),
    path('plans', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('checkout', CheckoutView.as_view(), name='subscription-checkout'),
    path('verify-payment', VerifyPaymentView.as_view(), name='subscription-verify-payment'),
    path('webhooks/razorpay', RazorpayWebhookView.as_view(), name='subscription-webhook'),
]
