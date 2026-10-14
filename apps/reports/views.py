import csv
import io
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from apps.common.permissions import IsTenantMember
from apps.reports.selectors import get_attendance_report, get_leave_report, get_payroll_register
from apps.payroll.models import PayrollRun

class AttendanceReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if not start_date or not end_date:
            return Response({'error': {'message': 'start_date and end_date are required (YYYY-MM-DD).'}}, status=status.HTTP_400_BAD_REQUEST)

        report = get_attendance_report(request.organization, start_date, end_date)
        return Response(report)

class LeaveReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        from django.utils import timezone
        year = int(request.query_params.get('year', timezone.now().year))
        report = get_leave_report(request.organization, year)
        return Response(report)

class PayrollReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        payroll_run_id = request.query_params.get('payroll_run')
        if not payroll_run_id:
            # Return list of closed/approved runs
            runs = PayrollRun.objects.filter(organization=request.organization).values(
                'id', 'month', 'year', 'state', 'total_gross', 'total_deductions', 'total_net'
            )
            return Response({'runs': list(runs)})

        data = get_payroll_register(request.organization, payroll_run_id)
        if not data:
            return Response({'error': {'message': 'Payroll run not found.'}}, status=status.HTTP_404_NOT_FOUND)

        run = data['payroll_run']
        items = data['items']

        items_data = [
            {
                'employee_code': item.employee.employee_code,
                'employee_name': item.employee.full_name,
                'department': item.employee.department.name,
                'calendar_days': item.calendar_days,
                'payable_days': item.payable_days,
                'lop_days': item.lop_days,
                'gross_earnings': item.gross_earnings,
                'total_deductions': item.total_deductions,
                'net_salary': item.net_salary,
            }
            for item in items
        ]

        return Response({
            'payroll_run': {
                'id': str(run.id),
                'month': run.month,
                'year': run.year,
                'state': run.state,
                'total_gross': run.total_gross,
                'total_deductions': run.total_deductions,
                'total_net': run.total_net,
            },
            'items': items_data
        })

class PayrollExportCSVView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        payroll_run_id = request.query_params.get('payroll_run')
        if not payroll_run_id:
            return Response({'error': {'message': 'payroll_run query parameter is required.'}}, status=status.HTTP_400_BAD_REQUEST)

        data = get_payroll_register(request.organization, payroll_run_id)
        if not data:
            return Response({'error': {'message': 'Payroll run not found.'}}, status=status.HTTP_404_NOT_FOUND)

        run = data['payroll_run']
        items = data['items']

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Employee Code', 'Employee Name', 'Department', 'Designation',
            'Calendar Days', 'Payable Days', 'LOP Days', 'Overtime Hours',
            'Gross Earnings (INR)', 'Total Deductions (INR)', 'Net Payable (INR)'
        ])

        for item in items:
            writer.writerow([
                item.employee.employee_code,
                item.employee.full_name,
                item.employee.department.name,
                item.employee.designation,
                item.calendar_days,
                item.payable_days,
                item.lop_days,
                item.overtime_hours,
                item.gross_earnings,
                item.total_deductions,
                item.net_salary
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="payroll_register_{run.year}_{run.month:02d}.csv"'
        return response
