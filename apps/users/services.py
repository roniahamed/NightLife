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

import random
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from .models import UserOTP, UserFollow, UserBlock

User = get_user_model()

class AuthService:
    @staticmethod
    def generate_and_send_otp(user, otp_type='register'):
        # Invalidate old OTPs of the same type
        UserOTP.objects.filter(user=user, otp_type=otp_type, is_used=False).update(is_used=True)
        
        # Generate 4 digit OTP
        otp = str(random.randint(1000, 9999))
        otp_hash = make_password(otp)
        expires_at = timezone.now() + timedelta(minutes=10)
        
        UserOTP.objects.create(user=user, otp_type=otp_type, otp_hash=otp_hash, expires_at=expires_at)
        
        subject = 'Your NightLife Verification Code' if otp_type == 'register' else 'NightLife Password Reset Code'
        message = f'Your 4-digit verification code is: {otp}\nIt expires in 10 minutes.'
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nightlife.local'),
            recipient_list=[user.email],
            fail_silently=False,
        )

    @staticmethod
    def verify_registration_otp(email, otp):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("User not found.")
            
        otp_record = UserOTP.objects.filter(user=user, otp_type='register', is_used=False).order_by('-created_at').first()
        
        if not otp_record or not otp_record.is_valid():
            raise ValueError("OTP expired or not found.")
            
        if check_password(otp, otp_record.otp_hash):
            otp_record.is_used = True
            otp_record.save()
            
            user.is_email_verified = True
            user.is_active = True
            user.save()
            
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        else:
            raise ValueError("Invalid OTP.")

    @staticmethod
    def resend_registration_otp(email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("User not found.")
        
        if user.is_active:
            raise ValueError("Account is already verified and active.")
            
        AuthService.generate_and_send_otp(user, otp_type='register')

    @staticmethod
    def request_password_reset_otp(email):
        try:
            user = User.objects.get(email=email)
            AuthService.generate_and_send_otp(user, otp_type='reset')
        except User.DoesNotExist:
            pass # Silent fail for security

    @staticmethod
    def verify_password_reset_otp(email, otp):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("User not found.")
            
        otp_record = UserOTP.objects.filter(user=user, otp_type='reset', is_used=False).order_by('-created_at').first()
        if not otp_record or not otp_record.is_valid():
            raise ValueError("OTP expired or not found.")
            
        if check_password(otp, otp_record.otp_hash):
            otp_record.is_used = True
            otp_record.save()
            
            # Generate token
            token = default_token_generator.make_token(user)
            return token
        else:
            raise ValueError("Invalid OTP.")

    @staticmethod
    def reset_password_with_token(email, token, new_password):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("User not found.")
            
        if default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
        else:
            raise ValueError("Invalid or expired token.")

    @staticmethod
    def change_password(user, old_password, new_password):
        if not user.check_password(old_password):
            raise ValueError("Incorrect old password.")
        user.set_password(new_password)
        user.save()


class SocialConnectionService:
    @staticmethod
    def toggle_follow(follower, target_username):
        if follower.username == target_username:
            raise ValueError("You cannot follow yourself.")
        
        target_user = get_object_or_404(User, username=target_username)
        
        # Check block status
        if UserBlock.objects.filter(blocker=target_user, blocked=follower).exists() or \
           UserBlock.objects.filter(blocker=follower, blocked=target_user).exists():
            raise PermissionDenied("Cannot perform this action.")

        follow, created = UserFollow.objects.get_or_create(follower=follower, following=target_user)
        
        if not created:
            follow.delete()
            return False # Unfollowed
        return True # Followed

    @staticmethod
    def toggle_block(blocker, target_username):
        if blocker.username == target_username:
            raise ValueError("You cannot block yourself.")
        
        target_user = get_object_or_404(User, username=target_username)

        block, created = UserBlock.objects.get_or_create(blocker=blocker, blocked=target_user)
        
        if not created:
            block.delete()
            return False # Unblocked
        
        # If blocked, also unfollow each other
        UserFollow.objects.filter(follower=blocker, following=target_user).delete()
        UserFollow.objects.filter(follower=target_user, following=blocker).delete()

        return True # Blocked

