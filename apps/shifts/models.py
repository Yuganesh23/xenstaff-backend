from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class ShiftTemplate(TenantScopedModel):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_overnight = models.BooleanField(default=False)
    grace_period_minutes = models.PositiveIntegerField(default=15)
    break_duration_minutes = models.PositiveIntegerField(default=60)
    working_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.00)

    class Meta:
        verbose_name = 'Shift Template'
        verbose_name_plural = 'Shift Templates'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    def save(self, *args, **kwargs):
        # Auto-detect overnight shift if end_time <= start_time
        if self.end_time <= self.start_time:
            self.is_overnight = True
        super().save(*args, **kwargs)

class ShiftAssignment(UUIDModel, TimeStampedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='shift_assignments'
    )
    shift_template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    effective_from = models.DateField(db_index=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Shift Assignment'
        verbose_name_plural = 'Shift Assignments'
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.employee.employee_code} -> {self.shift_template.name} ({self.effective_from})"
