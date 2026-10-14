from django.db import models
from apps.common.models import UUIDModel, TimeStampedModel, TenantScopedModel

class Notification(TenantScopedModel):
    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='SYSTEM') # LEAVE, ATTENDANCE, PAYROLL, SYSTEM
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.email}: {self.title}"
