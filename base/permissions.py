from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to add or modify other admin users.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and is an admin
        return request.user and request.user.is_authenticated and request.user.is_staff 
