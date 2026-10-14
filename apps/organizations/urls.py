from django.urls import path
from apps.organizations.views import (
    CurrentOrganizationView, BranchListCreateView, BranchDetailView,
    DepartmentListCreateView, DepartmentDetailView, HolidayListCreateView
)

urlpatterns = [
    path('current', CurrentOrganizationView.as_view(), name='org-current'),
    path('branches', BranchListCreateView.as_view(), name='branch-list-create'),
    path('branches/<uuid:pk>', BranchDetailView.as_view(), name='branch-detail'),
    path('departments', DepartmentListCreateView.as_view(), name='department-list-create'),
    path('departments/<uuid:pk>', DepartmentDetailView.as_view(), name='department-detail'),
    path('holidays', HolidayListCreateView.as_view(), name='holiday-list-create'),
]
