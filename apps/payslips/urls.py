from django.urls import path
from apps.payslips.views import PayslipListView, PayslipDetailView, PayslipDownloadView

urlpatterns = [
    path('', PayslipListView.as_view(), name='payslip-list'),
    path('<uuid:pk>', PayslipDetailView.as_view(), name='payslip-detail'),
    path('<uuid:pk>/download', PayslipDownloadView.as_view(), name='payslip-download'),
]
