import uuid
from django.db import models
from django.utils import timezone

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'updated_at'])

class TenantQuerySet(models.QuerySet):
    def for_organization(self, organization):
        if hasattr(self.model, 'organization'):
            return self.filter(organization=organization, is_deleted=False)
        return self.filter(is_deleted=False)

    def active(self):
        return self.filter(is_deleted=False)

class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def for_organization(self, organization):
        return self.get_queryset().for_organization(organization)

class TenantScopedModel(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_related",
        db_index=True
    )

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
