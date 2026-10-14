from rest_framework import generics, permissions, status
from rest_framework.response import Response
from apps.common.permissions import IsTenantMember, IsOrganizationOwnerOrHR
from apps.organizations.models import Organization, Branch, Department, Holiday
from apps.organizations.serializers import (
    OrganizationSerializer, BranchSerializer, DepartmentSerializer, HolidaySerializer
)

class CurrentOrganizationView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_object(self):
        return self.request.organization

    def perform_update(self, serializer):
        # Only owners/HR can update organization details
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can update settings.")
        serializer.save()

class BranchListCreateView(generics.ListCreateAPIView):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return Branch.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can manage branches.")
        serializer.save(organization=self.request.organization)

class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return Branch.objects.filter(organization=self.request.organization)

class DepartmentListCreateView(generics.ListCreateAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return Department.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can manage departments.")
        serializer.save(organization=self.request.organization)

class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return Department.objects.filter(organization=self.request.organization)

class HolidayListCreateView(generics.ListCreateAPIView):
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return Holiday.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can manage holidays.")
        serializer.save(organization=self.request.organization)
