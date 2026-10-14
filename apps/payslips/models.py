from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class Payslip(TenantScopedModel):
    payroll_item = models.OneToOneField(
        'payroll.PayrollItem',
        on_delete=models.CASCADE,
        related_name='payslip'
    )
    payslip_number = models.CharField(max_length=64, unique=True, db_index=True)
    pdf_file_path = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Payslip'
        verbose_name_plural = 'Payslips'
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return f"Payslip {self.payslip_number} - {self.payroll_item.employee.full_name}"
