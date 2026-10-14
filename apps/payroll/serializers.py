from rest_framework import serializers
from apps.payroll.models import (
    SalaryStructure, SalaryComponent, EmployeeSalaryAssignment,
    PayrollRun, PayrollItem, PayrollCalculationLine, PayrollException
)

class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = [
            'id', 'name', 'code', 'component_type', 'calculation_type',
            'percentage_basis_code', 'amount_or_percentage', 'is_taxable'
        ]
        read_only_fields = ['id']

class SalaryStructureSerializer(serializers.ModelSerializer):
    components = SalaryComponentSerializer(many=True, read_only=True)

    class Meta:
        model = SalaryStructure
        fields = ['id', 'name', 'description', 'is_active', 'components', 'created_at']
        read_only_fields = ['id', 'created_at']

class EmployeeSalaryAssignmentSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    structure_name = serializers.CharField(source='salary_structure.name', read_only=True)

    class Meta:
        model = EmployeeSalaryAssignment
        fields = [
            'id', 'employee', 'employee_code', 'employee_name',
            'salary_structure', 'structure_name', 'monthly_ctc',
            'effective_from', 'effective_to', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class PayrollCalculationLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollCalculationLine
        fields = ['id', 'component_name', 'component_code', 'component_type', 'base_amount', 'calculated_amount']
        read_only_fields = ['id']

class PayrollItemSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    designation = serializers.CharField(source='employee.designation', read_only=True)
    lines = PayrollCalculationLineSerializer(many=True, read_only=True)

    class Meta:
        model = PayrollItem
        fields = [
            'id', 'employee', 'employee_code', 'employee_name', 'designation',
            'calendar_days', 'payable_days', 'lop_days', 'overtime_hours',
            'gross_earnings', 'total_deductions', 'net_salary', 'lines'
        ]
        read_only_fields = ['id']

class PayrollExceptionSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = PayrollException
        fields = ['id', 'employee', 'employee_code', 'employee_name', 'exception_type', 'severity', 'description', 'is_resolved']
        read_only_fields = ['id']

class PayrollRunSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    exceptions_count = serializers.IntegerField(source='exceptions.count', read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            'id', 'period_start', 'period_end', 'month', 'year', 'state',
            'calculation_divisor_type', 'total_gross', 'total_deductions', 'total_net',
            'approved_by', 'approved_by_name', 'approved_at', 'error_message',
            'items_count', 'exceptions_count', 'created_at'
        ]
        read_only_fields = ['id', 'state', 'total_gross', 'total_deductions', 'total_net', 'approved_by', 'approved_at', 'created_at']
