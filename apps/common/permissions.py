from rest_framework import permissions

def _ensure_tenant_context(request):
    if not (request.user and request.user.is_authenticated):
        return None, None

    if getattr(request, 'organization', None) and getattr(request, 'organization_membership', None):
        return request.organization, request.organization_membership

    from apps.accounts.models import OrganizationMembership
    org_id = request.headers.get('X-Organization-ID')
    memberships = OrganizationMembership.objects.filter(user=request.user, is_active=True).select_related('organization')

    if org_id:
        membership = memberships.filter(organization_id=org_id).first()
        if membership:
            request.organization = membership.organization
            request.organization_membership = membership
            return request.organization, request.organization_membership

    if memberships.exists():
        membership = memberships.first()
        request.organization = membership.organization
        request.organization_membership = membership
        return request.organization, request.organization_membership

    return None, None

class IsTenantMember(permissions.BasePermission):
    """
    Allows access only to authenticated users with a valid organization context.
    """
    message = "You must be an active member of the target organization."

    def has_permission(self, request, view):
        org, mem = _ensure_tenant_context(request)
        return bool(request.user and request.user.is_authenticated and org is not None and mem is not None)

class HasRole:
    """
    Factory creating a permission class that permits specified organization roles.
    """
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def __call__(self):
        roles = self.allowed_roles

        class RolePermission(permissions.BasePermission):
            message = f"Operation requires one of the following roles: {', '.join(roles)}"

            def has_permission(self, request, view):
                org, membership = _ensure_tenant_context(request)
                if not (request.user and request.user.is_authenticated and membership):
                    return False
                return membership.role in roles or membership.role == 'ORGANIZATION_OWNER'

        return RolePermission

class IsPlatformAdmin(permissions.BasePermission):
    """
    Allows access only to XenFirm platform administrators.
    """
    message = "Platform administrator authorization required."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_platform_admin', False)
        )

class IsOrganizationOwnerOrHR(permissions.BasePermission):
    message = "Organization Owner or HR Admin role required."

    def has_permission(self, request, view):
        org, membership = _ensure_tenant_context(request)
        if not (request.user and request.user.is_authenticated and membership):
            return False
        return membership.role in ['ORGANIZATION_OWNER', 'HR_ADMIN']

class IsPayrollManagerOrOwner(permissions.BasePermission):
    message = "Payroll Manager or Organization Owner role required."

    def has_permission(self, request, view):
        org, membership = _ensure_tenant_context(request)
        if not (request.user and request.user.is_authenticated and membership):
            return False
        return membership.role in ['ORGANIZATION_OWNER', 'PAYROLL_MANAGER']
