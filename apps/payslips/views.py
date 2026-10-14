from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import IsTenantMember
from apps.payslips.models import Payslip
from apps.payslips.serializers import PayslipSerializer
from apps.payslips.services import generate_payslip_pdf

class PayslipListView(generics.ListAPIView):
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        qs = Payslip.objects.filter(organization=self.request.organization).select_related(
            'payroll_item__employee__department',
            'payroll_item__employee__branch',
            'payroll_item__payroll_run'
        ).prefetch_related('payroll_item__lines')

        # Employee self-service isolation: Only view own published payslips
        if role == 'EMPLOYEE':
            qs = qs.filter(payroll_item__employee__user=self.request.user, is_published=True)
        else:
            emp_id = self.request.query_params.get('employee')
            if emp_id:
                qs = qs.filter(payroll_item__employee_id=emp_id)

        month = self.request.query_params.get('month')
        if month:
            qs = qs.filter(payroll_item__payroll_run__month=month)

        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(payroll_item__payroll_run__year=year)

        return qs

class PayslipDetailView(generics.RetrieveAPIView):
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        qs = Payslip.objects.filter(organization=self.request.organization).select_related(
            'payroll_item__employee__department',
            'payroll_item__employee__branch',
            'payroll_item__payroll_run'
        ).prefetch_related('payroll_item__lines')

        if role == 'EMPLOYEE':
            qs = qs.filter(payroll_item__employee__user=self.request.user, is_published=True)

        return qs

class PayslipDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request, pk):
        role = request.organization_membership.role
        payslip_qs = Payslip.objects.filter(organization=request.organization).select_related(
            'payroll_item__employee__department',
            'payroll_item__employee__branch',
            'payroll_item__payroll_run'
        )

        if role == 'EMPLOYEE':
            payslip_qs = payslip_qs.filter(payroll_item__employee__user=request.user, is_published=True)

        payslip = generics.get_object_or_404(payslip_qs, pk=pk)

        pdf_bytes = generate_payslip_pdf(payslip)
        filename = f"payslip_{payslip.payslip_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
