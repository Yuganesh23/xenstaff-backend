from django.urls import path
from apps.platform_admin.views import PlatformStatsView, PlatformOrganizationListView

urlpatterns = [
    path('stats', PlatformStatsView.as_view(), name='platform-stats'),
    path('organizations', PlatformOrganizationListView.as_view(), name='platform-orgs'),
]
