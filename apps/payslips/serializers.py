from rest_framework import serializers
from apps.payslips.models import Payslip
from apps.payroll.serializers import PayrollCalculationLineSerializer

class PayslipSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='payroll_item.employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='payroll_item.employee.full_name', read_only=True)
    designation = serializers.CharField(source='payroll_item.employee.designation', read_only=True)
    department_name = serializers.CharField(source='payroll_item.employee.department.name', read_only=True)
    month = serializers.IntegerField(source='payroll_item.payroll_run.month', read_only=True)
    year = serializers.IntegerField(source='payroll_item.payroll_run.year', read_only=True)
    calendar_days = serializers.IntegerField(source='payroll_item.calendar_days', read_only=True)
    payable_days = serializers.DecimalField(source='payroll_item.payable_days', max_digits=5, decimal_places=2, read_only=True)
    lop_days = serializers.DecimalField(source='payroll_item.lop_days', max_digits=5, decimal_places=2, read_only=True)
    gross_earnings = serializers.DecimalField(source='payroll_item.gross_earnings', max_digits=12, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(source='payroll_item.total_deductions', max_digits=12, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(source='payroll_item.net_salary', max_digits=12, decimal_places=2, read_only=True)
    lines = PayrollCalculationLineSerializer(source='payroll_item.lines', many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = [
            'id', 'payslip_number', 'employee_code', 'employee_name', 'designation',
            'department_name', 'month', 'year', 'calendar_days', 'payable_days',
            'lop_days', 'gross_earnings', 'total_deductions', 'net_salary',
            'is_published', 'published_at', 'lines', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
