from decimal import Decimal
from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class ComponentType(models.TextChoices):
    EARNING = 'EARNING', 'Earning'
    DEDUCTION = 'DEDUCTION', 'Deduction'

class CalculationType(models.TextChoices):
    FLAT = 'FLAT', 'Flat Amount'
    PERCENTAGE = 'PERCENTAGE', 'Percentage'

class SalaryStructure(TenantScopedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Salary Structure'
        verbose_name_plural = 'Salary Structures'
        ordering = ['name']

    def __str__(self):
        return self.name

class SalaryComponent(UUIDModel, TimeStampedModel):
    salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.CASCADE,
        related_name='components'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50) # BASIC, HRA, SPECIAL_ALLOWANCE, PF, PT, etc.
    component_type = models.CharField(max_length=20, choices=ComponentType.choices)
    calculation_type = models.CharField(max_length=20, choices=CalculationType.choices, default=CalculationType.FLAT)
    percentage_basis_code = models.CharField(max_length=50, blank=True) # e.g. CTC, BASIC
    amount_or_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    is_taxable = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Salary Component'
        verbose_name_plural = 'Salary Components'
        ordering = ['component_type', 'code']

    def __str__(self):
        return f"{self.salary_structure.name} - {self.name} ({self.code})"

class EmployeeSalaryAssignment(UUIDModel, TimeStampedModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='salary_assignments'
    )
    salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.PROTECT,
        related_name='employee_assignments'
    )
    monthly_ctc = models.DecimalField(max_digits=12, decimal_places=2)
    effective_from = models.DateField(db_index=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Employee Salary Assignment'
        verbose_name_plural = 'Employee Salary Assignments'
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.employee.employee_code} - CTC ₹{self.monthly_ctc} ({self.effective_from})"

class PayrollRunState(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    CALCULATING = 'CALCULATING', 'Calculating'
    REVIEW = 'REVIEW', 'Review'
    APPROVED = 'APPROVED', 'Approved'
    PUBLISHED = 'PUBLISHED', 'Published'
    CLOSED = 'CLOSED', 'Closed'
    FAILED = 'FAILED', 'Failed'

class PayrollRun(TenantScopedModel):
    period_start = models.DateField()
    period_end = models.DateField()
    month = models.PositiveSmallIntegerField() # 1 - 12
    year = models.PositiveIntegerField()
    state = models.CharField(
        max_length=20,
        choices=PayrollRunState.choices,
        default=PayrollRunState.DRAFT,
        db_index=True
    )
    calculation_divisor_type = models.CharField(max_length=30, default='CALENDAR_DAYS') # CALENDAR_DAYS, FIXED_30, ACTUAL_WORKING_DAYS
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payroll_runs'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Payroll Run'
        verbose_name_plural = 'Payroll Runs'
        unique_together = ('organization', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.organization.name} - Payroll {self.month:02d}/{self.year} ({self.state})"

class PayrollItem(UUIDModel, TimeStampedModel):
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='items'
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_items'
    )
    calendar_days = models.PositiveIntegerField()
    payable_days = models.DecimalField(max_digits=5, decimal_places=2)
    lop_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Payroll Item'
        verbose_name_plural = 'Payroll Items'
        unique_together = ('payroll_run', 'employee')
        ordering = ['employee__employee_code']

    def __str__(self):
        return f"{self.employee.employee_code} - Net: ₹{self.net_salary}"

class PayrollCalculationLine(UUIDModel, TimeStampedModel):
    payroll_item = models.ForeignKey(
        PayrollItem,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    component_name = models.CharField(max_length=100)
    component_code = models.CharField(max_length=50)
    component_type = models.CharField(max_length=20, choices=ComponentType.choices)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Payroll Calculation Line'
        verbose_name_plural = 'Payroll Calculation Lines'
        ordering = ['component_type', 'component_code']

    def __str__(self):
        return f"{self.component_code}: ₹{self.calculated_amount}"

class PayrollException(UUIDModel, TimeStampedModel):
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='exceptions'
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_exceptions'
    )
    exception_type = models.CharField(max_length=50) # MISSING_SALARY_STRUCTURE, NEGATIVE_NET_SALARY, UNRESOLVED_ATTENDANCE
    severity = models.CharField(max_length=20, default='ERROR') # WARNING, ERROR
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['severity', 'created_at']

    def __str__(self):
        return f"{self.exception_type} for {self.employee.employee_code}"
