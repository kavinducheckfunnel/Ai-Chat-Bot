from rest_framework.permissions import BasePermission


def _get_role(user):
    """Returns the user's role string, or None if no profile."""
    try:
        return user.profile.role
    except Exception:
        return None


class IsSuperAdmin(BasePermission):
    """Allows access only to users with role='superadmin'."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and _get_role(request.user) == 'superadmin'
        )


class IsTenantAdmin(BasePermission):
    """Allows access to tenant_admin and superadmin users."""

    def has_permission(self, request, view):
        role = _get_role(request.user)
        return (
            request.user
            and request.user.is_authenticated
            and role in ('tenant_admin', 'superadmin')
        )


class IsOwnerOrSuperAdmin(BasePermission):
    """
    Object-level: allows access if user is superadmin, or if the object's
    related tenant is the requesting user.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if _get_role(request.user) == 'superadmin':
            return True
        # Check if the object is owned by the requesting tenant
        try:
            return obj.tenant_owners.filter(user=request.user).exists()
        except AttributeError:
            return False
