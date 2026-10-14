from rest_framework import serializers
from apps.attendance.models import AttendanceEvent, DailyAttendanceSummary, AttendanceCorrection

class AttendanceEventSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = AttendanceEvent
        fields = [
            'id', 'employee', 'employee_code', 'employee_name',
            'event_type', 'server_timestamp', 'client_timestamp',
            'idempotency_key', 'source'
        ]
        read_only_fields = ['id', 'server_timestamp']

class DailyAttendanceSummarySerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    work_hours = serializers.SerializerMethodField()

    class Meta:
        model = DailyAttendanceSummary
        fields = [
            'id', 'employee', 'employee_code', 'employee_name', 'date',
            'first_clock_in', 'last_clock_out', 'total_work_minutes', 'work_hours',
            'break_minutes', 'overtime_minutes', 'status',
            'is_late', 'is_early_departure', 'is_locked'
        ]
        read_only_fields = ['id', 'is_locked']

    def get_work_hours(self, obj):
        return round(obj.total_work_minutes / 60.0, 2)

class ClockInOutActionSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField(required=False)
    idempotency_key = serializers.CharField(max_length=64)
    client_timestamp = serializers.DateTimeField(required=False)
    source = serializers.CharField(default='WEB')

class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    date = serializers.DateField(source='summary.date', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = AttendanceCorrection
        fields = [
            'id', 'employee', 'employee_code', 'employee_name', 'summary', 'date',
            'requested_clock_in', 'requested_clock_out', 'reason',
            'status', 'reviewed_by', 'reviewed_by_email', 'rejection_reason',
            'created_at'
        ]
        read_only_fields = ['id', 'status', 'reviewed_by', 'created_at']
