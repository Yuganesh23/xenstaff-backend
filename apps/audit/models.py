from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class AuditLog(TenantScopedModel):
    actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    action = models.CharField(max_length=100, db_index=True) # e.g. PAYROLL_APPROVED, SALARY_UPDATED, EMPLOYEE_TERMINATED
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'action']),
            models.Index(fields=['organization', 'entity_type']),
        ]

    def __str__(self):
        actor_email = self.actor.email if self.actor else "System"
        return f"{self.action} on {self.entity_type} by {actor_email}"
