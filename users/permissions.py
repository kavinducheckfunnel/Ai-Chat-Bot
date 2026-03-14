from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Allows access only to users with superadmin role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        profile = getattr(request.user, 'profile', None)
        return profile is not None and profile.role == 'superadmin'


class IsTenantAdmin(BasePermission):
    """Allows access to tenant_admin or superadmin users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        profile = getattr(request.user, 'profile', None)
        return profile is not None and profile.role in ('superadmin', 'tenant_admin')


def get_accessible_clients(user):
    """
    Return the queryset of Client objects this user may access.
    Superadmins see all clients.
    Tenant admins see only clients assigned to their TenantProfile.
    """
    from users.models import Client
    if user.is_superuser:
        return Client.objects.all()
    profile = getattr(user, 'profile', None)
    if profile and profile.role == 'superadmin':
        return Client.objects.all()
    tenant = getattr(user, 'tenant_profile', None)
    if tenant:
        return tenant.clients.all()
    return Client.objects.none()
