from rest_framework import serializers
from apps.audit.models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'actor', 'actor_email', 'actor_name', 'action', 'entity_type', 'entity_id', 'changes', 'ip_address', 'created_at']
        read_only_fields = ['id', 'created_at']
