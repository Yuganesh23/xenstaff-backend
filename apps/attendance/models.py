from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class AttendanceEventType(models.TextChoices):
    CLOCK_IN = 'CLOCK_IN', 'Clock In'
    CLOCK_OUT = 'CLOCK_OUT', 'Clock Out'

class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', 'Present'
    HALF_DAY = 'HALF_DAY', 'Half Day'
    ABSENT = 'ABSENT', 'Absent'
    PAID_LEAVE = 'PAID_LEAVE', 'Paid Leave'
    UNPAID_LEAVE = 'UNPAID_LEAVE', 'Unpaid Leave (LOP)'
    WEEKLY_OFF = 'WEEKLY_OFF', 'Weekly Off'
    HOLIDAY = 'HOLIDAY', 'Holiday'

class AttendanceEvent(TenantScopedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_events'
    )
    event_type = models.CharField(max_length=20, choices=AttendanceEventType.choices)
    server_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    client_timestamp = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, db_index=True)
    source = models.CharField(max_length=30, default='WEB') # WEB, PWA, MANUAL

    class Meta:
        verbose_name = 'Attendance Event'
        verbose_name_plural = 'Attendance Events'
        ordering = ['-server_timestamp']

    def __str__(self):
        return f"{self.employee.employee_code} - {self.event_type} at {self.server_timestamp}"

class DailyAttendanceSummary(TenantScopedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_summaries'
    )
    date = models.DateField(db_index=True)
    first_clock_in = models.DateTimeField(null=True, blank=True)
    last_clock_out = models.DateTimeField(null=True, blank=True)
    total_work_minutes = models.PositiveIntegerField(default=0)
    break_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=30,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        db_index=True
    )
    is_late = models.BooleanField(default=False)
    is_early_departure = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False) # Locked when payroll is approved/closed

    class Meta:
        verbose_name = 'Daily Attendance Summary'
        verbose_name_plural = 'Daily Attendance Summaries'
        unique_together = ('employee', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['organization', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.date}: {self.status}"

class CorrectionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'

class AttendanceCorrection(TenantScopedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_corrections'
    )
    summary = models.ForeignKey(
        DailyAttendanceSummary,
        on_delete=models.CASCADE,
        related_name='corrections'
    )
    requested_clock_in = models.DateTimeField()
    requested_clock_out = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=CorrectionStatus.choices,
        default=CorrectionStatus.PENDING,
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_attendance_corrections'
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Attendance Correction'
        verbose_name_plural = 'Attendance Corrections'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.employee_code} Correction ({self.status}) for {self.summary.date}"
