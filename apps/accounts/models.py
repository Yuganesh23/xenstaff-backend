import secrets
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from apps.common.models import UUIDModel, TimeStampedModel

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_platform_admin', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin, UUIDModel, TimeStampedModel):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_platform_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.first_name} {self.last_name})".strip()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

class OrganizationRole(models.TextChoices):
    PLATFORM_ADMIN = 'PLATFORM_ADMIN', 'Platform Administrator'
    ORGANIZATION_OWNER = 'ORGANIZATION_OWNER', 'Organization Owner'
    HR_ADMIN = 'HR_ADMIN', 'HR Administrator'
    PAYROLL_MANAGER = 'PAYROLL_MANAGER', 'Payroll Manager'
    BRANCH_MANAGER = 'BRANCH_MANAGER', 'Branch Manager'
    TEAM_LEAD = 'TEAM_LEAD', 'Team Lead'
    EMPLOYEE = 'EMPLOYEE', 'Employee'
    AUDITOR = 'AUDITOR', 'Auditor'

class OrganizationMembership(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=30, choices=OrganizationRole.choices, default=OrganizationRole.EMPLOYEE)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Organization Membership'
        verbose_name_plural = 'Organization Memberships'
        unique_together = ('user', 'organization')
        indexes = [
            models.Index(fields=['user', 'organization']),
            models.Index(fields=['organization', 'role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"

class AuthToken(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_tokens')
    key = models.CharField(max_length=64, unique=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token for {self.user.email}"
