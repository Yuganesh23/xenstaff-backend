from rest_framework import serializers
from apps.employees.models import Employee, EmploymentHistory, EmploymentStatus, EmploymentType
from apps.organizations.models import Branch, Department

class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    reporting_manager_name = serializers.CharField(source='reporting_manager.full_name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'date_of_birth', 'gender',
            'joining_date', 'exit_date', 'employment_status', 'employment_type',
            'branch', 'branch_name', 'department', 'department_name',
            'designation', 'reporting_manager', 'reporting_manager_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    reporting_manager_name = serializers.CharField(source='reporting_manager.full_name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'date_of_birth', 'gender',
            'joining_date', 'exit_date', 'employment_status', 'employment_type',
            'branch', 'branch_name', 'department', 'department_name',
            'designation', 'reporting_manager', 'reporting_manager_name',
            'pan_number', 'aadhaar_last_four', 'bank_account_number', 'bank_ifsc', 'bank_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_branch(self, value):
        request = self.context.get('request')
        if request and hasattr(request, 'organization') and value.organization != request.organization:
            raise serializers.ValidationError("Specified branch does not belong to your organization.")
        return value

    def validate_department(self, value):
        request = self.context.get('request')
        if request and hasattr(request, 'organization') and value.organization != request.organization:
            raise serializers.ValidationError("Specified department does not belong to your organization.")
        return value

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and hasattr(request, 'organization_membership'):
            role = request.organization_membership.role
            # Mask sensitive data if not privileged
            if role not in ['ORGANIZATION_OWNER', 'HR_ADMIN', 'PAYROLL_MANAGER']:
                ret['pan_number'] = '••••••••' if ret.get('pan_number') else ''
                ret['bank_account_number'] = '••••••••' if ret.get('bank_account_number') else ''
        return ret

class EmployeeCSVImportRowSerializer(serializers.Serializer):
    employee_code = serializers.CharField(max_length=50)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    joining_date = serializers.DateField()
    branch_code = serializers.CharField(max_length=50)
    department_code = serializers.CharField(max_length=50)
    designation = serializers.CharField(max_length=150)
    employment_type = serializers.ChoiceField(choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
