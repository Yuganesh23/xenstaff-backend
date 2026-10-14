from django.urls import path
from apps.employees.views import (
    EmployeeListCreateView, EmployeeDetailView, EmployeeImportView, EmployeeExportView
)

urlpatterns = [
    path('', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('<uuid:pk>', EmployeeDetailView.as_view(), name='employee-detail'),
    path('import', EmployeeImportView.as_view(), name='employee-import'),
    path('export', EmployeeExportView.as_view(), name='employee-export'),
]
