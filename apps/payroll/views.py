from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import IsTenantMember, IsPayrollManagerOrOwner
from apps.payroll.models import (
    SalaryStructure, EmployeeSalaryAssignment, PayrollRun,
    PayrollItem, PayrollException
)
from apps.payroll.serializers import (
    SalaryStructureSerializer, EmployeeSalaryAssignmentSerializer,
    PayrollRunSerializer, PayrollItemSerializer, PayrollExceptionSerializer
)
from apps.payroll.services.engine import (
    calculate_payroll_run, approve_payroll_run, publish_payroll_run,
    close_payroll_run, revise_payroll_run
)

class SalaryStructureListCreateView(generics.ListCreateAPIView):
    serializer_class = SalaryStructureSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return SalaryStructure.objects.filter(organization=self.request.organization).prefetch_related('components')

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN', 'PAYROLL_MANAGER']:
            self.permission_denied(self.request, message="Privileged payroll role required.")
        serializer.save(organization=self.request.organization)

class SalaryStructureDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SalaryStructureSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return SalaryStructure.objects.filter(organization=self.request.organization).prefetch_related('components')

class EmployeeSalaryAssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSalaryAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        qs = EmployeeSalaryAssignment.objects.filter(employee__organization=self.request.organization).select_related(
            'employee', 'salary_structure'
        )
        emp_id = self.request.query_params.get('employee')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        return qs

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN', 'PAYROLL_MANAGER']:
            self.permission_denied(self.request, message="Privileged payroll role required.")
        serializer.save()

class PayrollRunListCreateView(generics.ListCreateAPIView):
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return PayrollRun.objects.filter(organization=self.request.organization).select_related('approved_by')

    def perform_create(self, serializer):
        if self.request.organization_membership.role not in ['ORGANIZATION_OWNER', 'PAYROLL_MANAGER']:
            self.permission_denied(self.request, message="Only Organization Owner or Payroll Manager can initiate payroll runs.")
        serializer.save(organization=self.request.organization)

class PayrollRunDetailView(generics.RetrieveAPIView):
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return PayrollRun.objects.filter(organization=self.request.organization).select_related('approved_by')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_serializer(instance).data
        # Include items breakdown
        items = instance.items.all().select_related('employee').prefetch_related('lines')
        data['items'] = PayrollItemSerializer(items, many=True).data
        return Response(data)

class PayrollRunCalculateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPayrollManagerOrOwner]

    def post(self, request, pk):
        payroll_run = generics.get_object_or_404(
            PayrollRun.objects.filter(organization=request.organization),
            pk=pk
        )
        calculated_run = calculate_payroll_run(payroll_run)
        return Response(PayrollRunSerializer(calculated_run).data)

class PayrollRunExceptionsView(generics.ListAPIView):
    serializer_class = PayrollExceptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        payroll_run_id = self.kwargs['pk']
        return PayrollException.objects.filter(
            payroll_run_id=payroll_run_id,
            payroll_run__organization=self.request.organization
        ).select_related('employee')

class PayrollRunApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPayrollManagerOrOwner]

    def post(self, request, pk):
        payroll_run = generics.get_object_or_404(
            PayrollRun.objects.filter(organization=request.organization),
            pk=pk
        )
        approved_run = approve_payroll_run(payroll_run, request.user)
        return Response(PayrollRunSerializer(approved_run).data)

class PayrollRunPublishView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPayrollManagerOrOwner]

    def post(self, request, pk):
        payroll_run = generics.get_object_or_404(
            PayrollRun.objects.filter(organization=request.organization),
            pk=pk
        )
        published_run = publish_payroll_run(payroll_run)
        return Response(PayrollRunSerializer(published_run).data)

class PayrollRunCloseView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPayrollManagerOrOwner]

    def post(self, request, pk):
        payroll_run = generics.get_object_or_404(
            PayrollRun.objects.filter(organization=request.organization),
            pk=pk
        )
        closed_run = close_payroll_run(payroll_run)
        return Response(PayrollRunSerializer(closed_run).data)

class PayrollRunReviseView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPayrollManagerOrOwner]

    def post(self, request, pk):
        payroll_run = generics.get_object_or_404(
            PayrollRun.objects.filter(organization=request.organization),
            pk=pk
        )
        revised_run = revise_payroll_run(payroll_run, request.user)
        return Response(PayrollRunSerializer(revised_run).data)
