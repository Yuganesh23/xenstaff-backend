from django.urls import path
from apps.shifts.views import ShiftTemplateListCreateView, ShiftAssignmentListCreateView

urlpatterns = [
    path('', ShiftTemplateListCreateView.as_view(), name='shift-list-create'),
    path('assignments', ShiftAssignmentListCreateView.as_view(), name='shift-assignment-list-create'),
]
