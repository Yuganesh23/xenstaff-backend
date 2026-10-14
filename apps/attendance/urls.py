from django.urls import path
from apps.attendance.views import (
    ClockInView, ClockOutView, AttendanceSummaryListView,
    AttendanceSummaryMetricsView, AttendanceCorrectionListCreateView,
    AttendanceCorrectionApproveView, AttendanceCorrectionRejectView
)

urlpatterns = [
    path('clock-in', ClockInView.as_view(), name='attendance-clock-in'),
    path('clock-out', ClockOutView.as_view(), name='attendance-clock-out'),
    path('', AttendanceSummaryListView.as_view(), name='attendance-list'),
    path('summary', AttendanceSummaryMetricsView.as_view(), name='attendance-metrics'),
    path('corrections', AttendanceCorrectionListCreateView.as_view(), name='attendance-corrections-list-create'),
    path('corrections/<uuid:pk>/approve', AttendanceCorrectionApproveView.as_view(), name='attendance-correction-approve'),
    path('corrections/<uuid:pk>/reject', AttendanceCorrectionRejectView.as_view(), name='attendance-correction-reject'),
]
