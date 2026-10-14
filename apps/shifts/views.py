from rest_framework import generics, permissions
from apps.common.permissions import IsTenantMember, IsOrganizationOwnerOrHR
from apps.shifts.models import ShiftTemplate, ShiftAssignment
from apps.shifts.serializers import ShiftTemplateSerializer, ShiftAssignmentSerializer

class ShiftTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = ShiftTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return ShiftTemplate.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can create shift templates.")
        serializer.save(organization=self.request.organization)

class ShiftAssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = ShiftAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        qs = ShiftAssignment.objects.filter(employee__organization=self.request.organization).select_related(
            'employee', 'shift_template'
        )
        emp_id = self.request.query_params.get('employee')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        return qs

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can assign shifts.")
        serializer.save()
