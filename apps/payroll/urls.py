from django.urls import path
from apps.payroll.views import (
    SalaryStructureListCreateView, SalaryStructureDetailView,
    EmployeeSalaryAssignmentListCreateView, PayrollRunListCreateView,
    PayrollRunDetailView, PayrollRunCalculateView, PayrollRunExceptionsView,
    PayrollRunApproveView, PayrollRunPublishView, PayrollRunCloseView,
    PayrollRunReviseView
)

urlpatterns = [
    path('salary-structures', SalaryStructureListCreateView.as_view(), name='salary-structures-list-create'),
    path('salary-structures/<uuid:pk>', SalaryStructureDetailView.as_view(), name='salary-structures-detail'),
    path('salary-assignments', EmployeeSalaryAssignmentListCreateView.as_view(), name='salary-assignments-list-create'),
    path('runs', PayrollRunListCreateView.as_view(), name='payroll-runs-list-create'),
    path('runs/<uuid:pk>', PayrollRunDetailView.as_view(), name='payroll-run-detail'),
    path('runs/<uuid:pk>/calculate', PayrollRunCalculateView.as_view(), name='payroll-run-calculate'),
    path('runs/<uuid:pk>/exceptions', PayrollRunExceptionsView.as_view(), name='payroll-run-exceptions'),
    path('runs/<uuid:pk>/approve', PayrollRunApproveView.as_view(), name='payroll-run-approve'),
    path('runs/<uuid:pk>/publish', PayrollRunPublishView.as_view(), name='payroll-run-publish'),
    path('runs/<uuid:pk>/close', PayrollRunCloseView.as_view(), name='payroll-run-close'),
    path('runs/<uuid:pk>/revise', PayrollRunReviseView.as_view(), name='payroll-run-revise'),
]
