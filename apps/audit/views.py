from rest_framework import generics, permissions
from apps.common.permissions import IsTenantMember
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer

class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        if role not in ['ORGANIZATION_OWNER', 'HR_ADMIN', 'AUDITOR']:
            return AuditLog.objects.none()

        qs = AuditLog.objects.filter(organization=self.request.organization).select_related('actor')
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs
