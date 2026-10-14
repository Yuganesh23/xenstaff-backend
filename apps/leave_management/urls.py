from django.urls import path
from apps.leave_management.views import (
    LeaveTypeListCreateView, LeaveBalanceListView, LeaveRequestListCreateView,
    LeaveRequestApproveView, LeaveRequestRejectView, LeaveRequestCancelView
)

urlpatterns = [
    path('types', LeaveTypeListCreateView.as_view(), name='leave-type-list-create'),
    path('balances', LeaveBalanceListView.as_view(), name='leave-balance-list'),
    path('requests', LeaveRequestListCreateView.as_view(), name='leave-request-list-create'),
    path('requests/<uuid:pk>/approve', LeaveRequestApproveView.as_view(), name='leave-request-approve'),
    path('requests/<uuid:pk>/reject', LeaveRequestRejectView.as_view(), name='leave-request-reject'),
    path('requests/<uuid:pk>/cancel', LeaveRequestCancelView.as_view(), name='leave-request-cancel'),
]
