from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from apps.common.permissions import IsPlatformAdmin
from apps.organizations.models import Organization
from apps.accounts.models import User, OrganizationMembership
from apps.subscriptions.models import Subscription, SubscriptionStatus

class PlatformStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        total_orgs = Organization.objects.count()
        total_users = User.objects.count()
        active_subs = Subscription.objects.filter(status=SubscriptionStatus.ACTIVE).count()
        trialing_subs = Subscription.objects.filter(status=SubscriptionStatus.TRIALING).count()

        return Response({
            'total_organizations': total_orgs,
            'total_users': total_users,
            'active_subscriptions': active_subs,
            'trialing_subscriptions': trialing_subs,
        })

class PlatformOrganizationListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        orgs = Organization.objects.all().order_by('-created_at')
        results = []
        for o in orgs:
            owner_membership = OrganizationMembership.objects.filter(organization=o, role='ORGANIZATION_OWNER').select_related('user').first()
            sub = Subscription.objects.filter(organization=o).select_related('plan').first()
            results.append({
                'id': str(o.id),
                'name': o.name,
                'slug': o.slug,
                'owner_email': owner_membership.user.email if owner_membership else 'N/A',
                'plan_name': sub.plan.name if sub else 'None',
                'subscription_status': sub.status if sub else 'N/A',
                'created_at': o.created_at,
            })
        return Response({'results': results})
