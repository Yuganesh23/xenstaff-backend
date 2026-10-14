from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class Organization(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    gstin = models.CharField(max_length=15, blank=True, null=True)
    pan = models.CharField(max_length=10, blank=True, null=True)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    currency = models.CharField(max_length=3, default='INR')
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=4) # April
    is_active = models.BooleanField(default=True)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.CharField(max_length=50, default='INITIAL')

    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['name']

    def __str__(self):
        return self.name

class Branch(TenantScopedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    is_headquarters = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'
        unique_together = ('organization', 'code')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class Department(TenantScopedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_departments')

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        unique_together = ('organization', 'code')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class Holiday(TenantScopedModel):
    name = models.CharField(max_length=150)
    date = models.DateField(db_index=True)
    is_optional = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'
        unique_together = ('organization', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.name} ({self.date})"
