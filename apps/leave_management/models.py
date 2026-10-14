from decimal import Decimal
from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class LeaveType(TenantScopedModel):
    name = models.CharField(max_length=50) # Casual Leave, Sick Leave, Earned Leave, LOP
    code = models.CharField(max_length=10) # CL, SL, EL, LOP
    annual_quota = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('12.00'))
    is_paid = models.BooleanField(default=True)
    allows_half_day = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Leave Type'
        verbose_name_plural = 'Leave Types'
        unique_together = ('organization', 'code')
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.code})"

class LeaveBalance(TenantScopedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    year = models.PositiveIntegerField()
    allocated_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    pending_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'
        unique_together = ('employee', 'leave_type', 'year')
        ordering = ['year', 'leave_type']

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type.code} ({self.year}): {self.available_days} available"

    @property
    def available_days(self):
        return max(Decimal('0.00'), self.allocated_days - self.used_days - self.pending_days)

class LeaveRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'

class LeaveRequest(TenantScopedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests'
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    total_days = models.DecimalField(max_digits=4, decimal_places=2)
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.PENDING,
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leave_requests'
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return f"{self.employee.employee_code}: {self.leave_type.code} ({self.start_date} to {self.end_date}) [{self.status}]"

class LeaveLedgerEntry(TenantScopedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_ledger_entries'
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20) # ALLOCATION, DEBIT, CREDIT, CANCELLATION
    days = models.DecimalField(max_digits=5, decimal_places=2)
    balance_after = models.DecimalField(max_digits=5, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.employee_code} - {self.transaction_type}: {self.days} days"
