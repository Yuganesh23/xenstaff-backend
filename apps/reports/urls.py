from django.urls import path
from apps.reports.views import (
    AttendanceReportView, LeaveReportView, PayrollReportView, PayrollExportCSVView
)

urlpatterns = [
    path('attendance', AttendanceReportView.as_view(), name='report-attendance'),
    path('leave', LeaveReportView.as_view(), name='report-leave'),
    path('payroll', PayrollReportView.as_view(), name='report-payroll'),
    path('payroll/export', PayrollExportCSVView.as_view(), name='report-payroll-export'),
]
