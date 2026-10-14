from rest_framework import serializers
from apps.accounts.models import User, OrganizationMembership, OrganizationRole

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'is_platform_admin', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_platform_admin', 'is_active', 'created_at']

class OrganizationMembershipSerializer(serializers.ModelSerializer):
    organization_id = serializers.CharField(source='organization.id', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_slug = serializers.CharField(source='organization.slug', read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ['id', 'organization_id', 'organization_name', 'organization_slug', 'role', 'is_active']

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    company_name = serializers.CharField(max_length=200)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class SwitchOrganizationSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()

class InviteEmployeeSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()

class VerifyTokenSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

class SetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs
