from django.urls import resolve, Resolver404


class ApiSlashNormalizeMiddleware:
    """
    Middleware that seamlessly handles both trailing-slash and non-trailing-slash API routes.
    If an incoming API request cannot be resolved as-is, it attempts resolving the alternative
    (appending or stripping the trailing slash). If found, it updates request.path_info
    and request.path in-place, bypassing HTTP redirects and preventing POST APPEND_SLASH
    RuntimeError when requests are forwarded by Next.js proxy rewrites.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith('/api/'):
            try:
                resolve(request.path_info)
            except Resolver404:
                alt = request.path_info[:-1] if request.path_info.endswith('/') else f"{request.path_info}/"
                try:
                    resolve(alt)
                    request.path_info = alt
                    if hasattr(request, 'path'):
                        request.path = alt
                except Resolver404:
                    pass

        return self.get_response(request)


class TenantContextMiddleware:
    """
    Middleware that establishes the active organization context on the request object.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.organization_membership = None

        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check for explicitly supplied organization header
            org_id = request.headers.get('X-Organization-ID')
            
            from apps.accounts.models import OrganizationMembership
            memberships = OrganizationMembership.objects.filter(user=request.user, is_active=True).select_related('organization')
            
            if org_id:
                membership = memberships.filter(organization_id=org_id).first()
                if membership:
                    request.organization = membership.organization
                    request.organization_membership = membership
            
            # Fallback to first available membership if not set or invalid
            if not request.organization and memberships.exists():
                membership = memberships.first()
                request.organization = membership.organization
                request.organization_membership = membership

        response = self.get_response(request)
        return response
