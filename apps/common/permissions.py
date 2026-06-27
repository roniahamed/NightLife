from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` or `user` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Write permissions are only allowed to the owner of the snippet
        # Will check `owner` first, fallback to `user`
        owner = getattr(obj, 'owner', getattr(obj, 'user', None))
        return owner == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit it.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsActiveProfileUser(permissions.BasePermission):
    """
    Allows access only to authenticated users whose active profile is 'user'.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Default to checking registration_type if token doesn't have active_profile claim
        active_profile = request.auth.payload.get('active_profile') if hasattr(request, 'auth') and request.auth else request.user.registration_type
        return active_profile == 'user'

class IsActiveProfileVenue(permissions.BasePermission):
    """
    Allows access only to authenticated users whose active profile is 'venue'.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        active_profile = request.auth.payload.get('active_profile') if hasattr(request, 'auth') and request.auth else request.user.registration_type
        return active_profile == 'venue'
