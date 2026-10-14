from rest_framework import serializers
from apps.leave_management.models import LeaveType, LeaveBalance, LeaveRequest, LeaveLedgerEntry

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'code', 'annual_quota', 'is_paid', 'allows_half_day']
        read_only_fields = ['id']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    available_days = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'leave_type', 'leave_type_name', 'leave_type_code',
            'year', 'allocated_days', 'used_days', 'pending_days', 'available_days'
        ]
        read_only_fields = ['id', 'available_days']

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_code',
            'leave_type', 'leave_type_name', 'leave_type_code',
            'start_date', 'end_date', 'total_days', 'is_half_day',
            'reason', 'status', 'reviewed_by', 'reviewed_by_name',
            'rejection_reason', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'reviewed_by', 'created_at']

class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)

    class Meta:
        model = LeaveLedgerEntry
        fields = ['id', 'leave_type', 'leave_type_code', 'transaction_type', 'days', 'balance_after', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']
