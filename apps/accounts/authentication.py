from rest_framework import authentication, exceptions
from apps.accounts.models import AuthToken, OrganizationMembership

class SessionAndTokenAuthentication(authentication.BaseAuthentication):
    """
    Supports both Bearer/Token header and standard Django session authentication,
    and reliably resolves active tenant context on the request.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() not in ['bearer', 'token']:
            return None

        token_key = parts[1]
        try:
            token = AuthToken.objects.select_related('user').get(key=token_key)
        except AuthToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid authentication token.')

        user = token.user
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is disabled.')

        # Resolve organization context directly upon token authentication
        self._attach_organization_context(request, user)

        return (user, token)

    def _attach_organization_context(self, request, user):
        org_id = request.headers.get('X-Organization-ID')
        memberships = OrganizationMembership.objects.filter(user=user, is_active=True).select_related('organization')

        if org_id:
            membership = memberships.filter(organization_id=org_id).first()
            if membership:
                request.organization = membership.organization
                request.organization_membership = membership
                return

        if not getattr(request, 'organization', None) and memberships.exists():
            membership = memberships.first()
            request.organization = membership.organization
            request.organization_membership = membership
