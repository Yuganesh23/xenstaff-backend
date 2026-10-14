from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/organizations/', include('apps.organizations.urls')),
    path('api/v1/employees/', include('apps.employees.urls')),
    path('api/v1/shifts/', include('apps.shifts.urls')),
    path('api/v1/attendance/', include('apps.attendance.urls')),
    path('api/v1/leave/', include('apps.leave_management.urls')),
    path('api/v1/payroll/', include('apps.payroll.urls')),
    path('api/v1/payslips/', include('apps.payslips.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/platform/', include('apps.platform_admin.urls')),
]
