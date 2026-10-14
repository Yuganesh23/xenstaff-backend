from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class EmploymentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PROBATION = 'PROBATION', 'Probation'
    NOTICE_PERIOD = 'NOTICE_PERIOD', 'Notice Period'
    TERMINATED = 'TERMINATED', 'Terminated'
    RESIGNED = 'RESIGNED', 'Resigned'

class EmploymentType(models.TextChoices):
    FULL_TIME = 'FULL_TIME', 'Full-time'
    PART_TIME = 'PART_TIME', 'Part-time'
    CONTRACT = 'CONTRACT', 'Contract'
    INTERN = 'INTERN', 'Intern'

class Employee(TenantScopedModel):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profiles'
    )
    employee_code = models.CharField(max_length=50, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    joining_date = models.DateField(db_index=True)
    exit_date = models.DateField(null=True, blank=True)
    employment_status = models.CharField(
        max_length=30,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
        db_index=True
    )
    employment_type = models.CharField(
        max_length=30,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    branch = models.ForeignKey(
        'organizations.Branch',
        on_delete=models.PROTECT,
        related_name='employees'
    )
    department = models.ForeignKey(
        'organizations.Department',
        on_delete=models.PROTECT,
        related_name='employees'
    )
    designation = models.CharField(max_length=150)
    reporting_manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )

    # Sensitive compliance and banking details
    pan_number = models.CharField(max_length=10, blank=True)
    aadhaar_last_four = models.CharField(max_length=4, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        unique_together = ('organization', 'employee_code')
        ordering = ['employee_code']
        indexes = [
            models.Index(fields=['organization', 'employment_status']),
            models.Index(fields=['organization', 'department']),
            models.Index(fields=['organization', 'branch']),
        ]

    def __str__(self):
        return f"{self.employee_code} - {self.first_name} {self.last_name}".strip()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

class EmploymentHistory(UUIDModel, TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='history')
    effective_date = models.DateField()
    change_type = models.CharField(max_length=50) # e.g. PROMOTION, DESIGNATION_CHANGE, SALARY_REVISION
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255)
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-effective_date', '-created_at']

    def __str__(self):
        return f"{self.employee.employee_code}: {self.change_type} on {self.effective_date}"
