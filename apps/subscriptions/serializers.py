from rest_framework import serializers
from apps.subscriptions.models import SubscriptionPlan, Subscription, SubscriptionPayment

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'code', 'monthly_price', 'annual_price', 'max_employees', 'is_active']
        read_only_fields = ['id']

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    max_employees = serializers.IntegerField(source='plan.max_employees', read_only=True)
    monthly_price = serializers.DecimalField(source='plan.monthly_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'plan_name', 'plan_code', 'max_employees', 'monthly_price',
            'billing_interval', 'status', 'current_period_start', 'current_period_end',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CheckoutRequestSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=50)
    billing_interval = serializers.ChoiceField(choices=['MONTHLY', 'ANNUAL'], default='MONTHLY')

class VerifyPaymentSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=50)
    billing_interval = serializers.ChoiceField(choices=['MONTHLY', 'ANNUAL'], default='MONTHLY')
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=255)
