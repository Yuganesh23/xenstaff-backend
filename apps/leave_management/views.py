from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from apps.common.permissions import IsTenantMember, IsOrganizationOwnerOrHR
from apps.employees.models import Employee
from apps.leave_management.models import LeaveType, LeaveBalance, LeaveRequest, LeaveRequestStatus
from apps.leave_management.serializers import (
    LeaveTypeSerializer, LeaveBalanceSerializer, LeaveRequestSerializer
)
from apps.leave_management.services import (
    submit_leave_request, approve_leave_request, reject_leave_request, cancel_leave_request
)

class LeaveTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return LeaveType.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            self.permission_denied(self.request, message="Only Organization Owners and HR Admins can configure leave types.")
        serializer.save(organization=self.request.organization)

class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        current_year = timezone.now().year
        qs = LeaveBalance.objects.filter(
            organization=self.request.organization,
            year=current_year
        ).select_related('employee', 'leave_type')

        if role == 'EMPLOYEE':
            emp = Employee.objects.filter(organization=self.request.organization, user=self.request.user).first()
            if not emp:
                return LeaveBalance.objects.none()
            qs = qs.filter(employee=emp)
        else:
            emp_param = self.request.query_params.get('employee')
            if emp_param:
                qs = qs.filter(employee_id=emp_param)

        return qs

class LeaveRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        qs = LeaveRequest.objects.filter(organization=self.request.organization).select_related(
            'employee', 'leave_type', 'reviewed_by'
        )

        if role == 'EMPLOYEE':
            emp = Employee.objects.filter(organization=self.request.organization, user=self.request.user).first()
            if not emp:
                return LeaveRequest.objects.none()
            qs = qs.filter(employee=emp)
        else:
            emp_param = self.request.query_params.get('employee')
            if emp_param:
                qs = qs.filter(employee_id=emp_param)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs

    def create(self, request, *args, **kwargs):
        role = request.organization_membership.role
        # Resolve target employee
        emp_id = request.data.get('employee')
        if emp_id and role in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            employee = Employee.objects.filter(organization=request.organization, id=emp_id).first()
        else:
            employee = Employee.objects.filter(organization=request.organization, user=request.user).first()

        if not employee:
            return Response({'error': {'message': 'Employee profile required to apply for leave.'}}, status=status.HTTP_400_BAD_REQUEST)

        leave_type_id = request.data.get('leave_type')
        leave_type = generics.get_object_or_404(
            LeaveType.objects.filter(organization=request.organization),
            pk=leave_type_id
        )

        from decimal import Decimal
        total_days = Decimal(str(request.data.get('total_days', 1.0)))
        is_half_day = bool(request.data.get('is_half_day', False))
        reason = request.data.get('reason', '')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        from datetime import date
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        leave_req = submit_leave_request(
            organization=request.organization,
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            is_half_day=is_half_day,
            reason=reason
        )

        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)

class LeaveRequestApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request, pk):
        leave_req = generics.get_object_or_404(
            LeaveRequest.objects.filter(organization=request.organization),
            pk=pk
        )
        approved = approve_leave_request(leave_req, request.user)
        return Response(LeaveRequestSerializer(approved).data)

class LeaveRequestRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request, pk):
        leave_req = generics.get_object_or_404(
            LeaveRequest.objects.filter(organization=request.organization),
            pk=pk
        )
        rejection_reason = request.data.get('rejection_reason', 'Rejected by HR.')
        rejected = reject_leave_request(leave_req, request.user, rejection_reason=rejection_reason)
        return Response(LeaveRequestSerializer(rejected).data)

class LeaveRequestCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def post(self, request, pk):
        leave_req = generics.get_object_or_404(
            LeaveRequest.objects.filter(organization=request.organization),
            pk=pk
        )
        cancelled = cancel_leave_request(leave_req, request.user)
        return Response(LeaveRequestSerializer(cancelled).data)
