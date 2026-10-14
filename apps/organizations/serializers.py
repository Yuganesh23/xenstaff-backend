from rest_framework import serializers
from apps.organizations.models import Organization, Branch, Department, Holiday

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'legal_name', 'slug', 'gstin', 'pan',
            'timezone', 'currency', 'fiscal_year_start_month',
            'is_active', 'onboarding_completed', 'onboarding_step',
            'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code', 'city', 'state', 'address', 'is_headquarters', 'created_at']
        read_only_fields = ['id', 'created_at']

class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'parent', 'parent_name', 'created_at']
        read_only_fields = ['id', 'created_at']

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'date', 'is_optional', 'created_at']
        read_only_fields = ['id', 'created_at']
