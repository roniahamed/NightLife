from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken

class UserProfileService:
    @staticmethod
    def get_image_url(request, image_field):
        if image_field and hasattr(image_field, 'url'):
            if request:
                return request.build_absolute_uri(image_field.url)
            return image_field.url
        return None

    @classmethod
    def get_available_profiles(cls, user, request=None):
        profiles = []
        
        # Get active profile type from request auth token
        active_profile_type = 'user'
        if request and request.auth and isinstance(request.auth, dict) or hasattr(request.auth, 'get'):
            active_profile_type = request.auth.get('active_profile', 'user')
        elif hasattr(user, 'registration_type'):
            # Fallback if no valid token
            pass
            
        # 1. Add User Profile
        user_name = f"{user.first_name} {user.last_name}".strip() or user.username
        profiles.append({
            'id': str(user.id),
            'profile_type': 'user',
            'is_active': active_profile_type == 'user',
            'username': user.username,
            'name': user_name,
            'image': cls.get_image_url(request, user.profile_image),
            'cover_image': cls.get_image_url(request, user.cover_image)
        })
        
        # 2. Add Venue Profile if it exists
        if hasattr(user, 'venue_profile'):
            venue = user.venue_profile
            profiles.append({
                'id': str(venue.id),
                'profile_type': 'venue',
                'is_active': active_profile_type == 'venue',
                'username': venue.username,
                'name': venue.name,
                'image': cls.get_image_url(request, venue.profile_image),
                'cover_image': cls.get_image_url(request, venue.cover_image)
            })
            
        return profiles

    @staticmethod
    def switch_profile(user, target_profile, profile_id):
        if target_profile == 'venue':
            if not hasattr(user, 'venue_profile'):
                raise PermissionDenied("You do not have a venue profile.")
            if str(user.venue_profile.id) != str(profile_id):
                raise PermissionDenied("This venue profile does not belong to you.")
            if not user.venue_profile.is_approved:
                raise PermissionDenied("Your venue is pending admin approval.")
                
        elif target_profile == 'user':
            if str(user.id) != str(profile_id):
                raise PermissionDenied("This user profile does not belong to you.")
            
            # Auto-activate user profile if it was inactive
            if not user.is_user_profile_active:
                user.is_user_profile_active = True
                user.save(update_fields=['is_user_profile_active'])
        
        # Generate new token with new active_profile
        refresh = RefreshToken.for_user(user)
        refresh['active_profile'] = target_profile
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'active_profile': target_profile
        }
