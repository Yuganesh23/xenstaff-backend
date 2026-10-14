from rest_framework import serializers
from apps.shifts.models import ShiftTemplate, ShiftAssignment

class ShiftTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftTemplate
        fields = [
            'id', 'name', 'start_time', 'end_time', 'is_overnight',
            'grace_period_minutes', 'break_duration_minutes', 'working_hours',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ShiftAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    shift_name = serializers.CharField(source='shift_template.name', read_only=True)

    class Meta:
        model = ShiftAssignment
        fields = [
            'id', 'employee', 'employee_name', 'employee_code',
            'shift_template', 'shift_name', 'effective_from', 'effective_to',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
