import random
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import UserOTP, UserFollow, UserBlock, UserReport
from .serializers import (
    RegisterSerializer, VerifyOTPSerializer, ResendOTPSerializer, ForgotPasswordSerializer,
    VerifyResetOTPSerializer, ResetPasswordSerializer, ChangePasswordSerializer, ProfileSerializer,
    UserPublicProfileSerializer, UserFollowerSerializer, UserFollowingSerializer, UserReportSerializer,
    UserBlockedSerializer, UserSettingsSerializer, CustomTokenObtainPairSerializer,
    SwitchProfileRequestSerializer, AvailableProfilesResponseSerializer
)
from .services import UserProfileService, AuthService, SocialConnectionService
from apps.common.pagination import StandardResultsSetPagination
from apps.common.permissions import IsActiveProfileUser, IsActiveProfileVenue
from apps.common.utils import success_response, error_response
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as rf_serializers

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @extend_schema(summary="Register a new user", description="Creates an inactive user and sends a 4-digit OTP to email.", tags=['Authentication'])
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            AuthService.generate_and_send_otp(user, otp_type='register')
            
            return success_response(
                data={"email": user.email}, 
                message="User created successfully. Please check your email for the OTP.", 
                status=status.HTTP_201_CREATED
            )
        return error_response(errors=serializer.errors, message="Registration failed.", status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class SwitchProfileView(APIView):
    permission_classes = (IsAuthenticated,)
    
    @extend_schema(
        summary="Switch Profile", 
        description="Switch between 'user' and 'venue' profiles. Requires 'profile' target and the target 'profile_id'. Validates ownership of the profile and role permissions before returning a new JWT with updated active_profile.", 
        tags=['Authentication'],
        request=SwitchProfileRequestSerializer,
        responses={200: inline_serializer(name='SwitchProfileResponse', fields={'refresh': rf_serializers.CharField(), 'access': rf_serializers.CharField(), 'active_profile': rf_serializers.CharField()})}
    )
    def post(self, request):
        serializer = SwitchProfileRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message="Invalid data.", errors=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target = serializer.validated_data['profile']
        profile_id = serializer.validated_data['profile_id']
        
        from rest_framework.exceptions import PermissionDenied
        try:
            token_data = UserProfileService.switch_profile(request.user, target, profile_id)
        except PermissionDenied as e:
            return error_response(message=str(e), status=status.HTTP_403_FORBIDDEN)
            
        return success_response(
            data=token_data,
            message=f"Successfully switched to {target} profile."
        )

class AvailableProfilesView(APIView):
    permission_classes = (IsAuthenticated,)
    
    @extend_schema(
        summary="Get Available Profiles",
        description="Returns a list of all profiles (user and venue) that the authenticated user can switch to.",
        tags=['Authentication'],
        responses={200: AvailableProfilesResponseSerializer}
    )
    def get(self, request):
        profiles = UserProfileService.get_available_profiles(request.user, request=request)
        return success_response(
            data={'profiles': profiles},
            message="Available profiles fetched successfully."
        )

class VerifyOTPView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = VerifyOTPSerializer

    @extend_schema(summary="Verify OTP", description="Verifies the 4-digit OTP. On success, activates the account and returns JWT tokens.", tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        try:
            token_data = AuthService.verify_registration_otp(email, otp)
            return success_response(
                data=token_data,
                message="Email verified and logged in successfully.",
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            if str(e) == "User not found.":
                return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResendOTPSerializer

    @extend_schema(summary="Resend Registration OTP", description="Resends the 4-digit OTP to the user's email if the account is not yet verified.", tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(email=serializer.validated_data['email'])
            except User.DoesNotExist:
                return error_response(message="User not found.", status=status.HTTP_404_NOT_FOUND)
            
            if user.is_active:
                return error_response(message="Account is already verified and active.", status=status.HTTP_400_BAD_REQUEST)
                
            AuthService.generate_and_send_otp(user, otp_type='register')
            return success_response(message="A new OTP has been sent to your email.")
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ForgotPasswordSerializer

    @extend_schema(summary="Forgot Password", description="Generates and sends a 4-digit OTP to reset the password.", tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            AuthService.request_password_reset_otp(serializer.validated_data['email'])
            return success_response(message="If an account exists, an OTP was sent.")
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class VerifyResetOTPView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = VerifyResetOTPSerializer

    @extend_schema(summary="Verify Reset OTP", description="Verifies OTP for password reset and returns a reset token.", tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                token = AuthService.verify_password_reset_otp(
                    serializer.validated_data['email'], 
                    serializer.validated_data['otp']
                )
                return success_response(
                    data={"token": token},
                    message="OTP verified. Use this token and your email to reset password."
                )
            except ValueError as e:
                if str(e) == "User not found.":
                    return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializer

    @extend_schema(summary="Reset Password", description="Uses the reset token to set a new password.", tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                AuthService.reset_password_with_token(
                    serializer.validated_data['email'],
                    serializer.validated_data['token'],
                    serializer.validated_data['new_password']
                )
                return success_response(message="Password reset successfully.")
            except ValueError as e:
                if str(e) == "User not found.":
                    return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    @extend_schema(summary="Change Password", description="Change password using old password.", tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                AuthService.change_password(
                    request.user,
                    serializer.validated_data['old_password'],
                    serializer.validated_data['new_password']
                )
                return success_response(message="Password changed successfully.")
            except ValueError as e:
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_class(self):
        if getattr(self, "swagger_fake_view", False):
            return ProfileSerializer
            
        active_profile = 'user'
        if hasattr(self.request, 'auth') and self.request.auth and hasattr(self.request.auth, 'payload'):
            active_profile = self.request.auth.payload.get('active_profile', 'user')
            
        if active_profile == 'venue':
            from apps.venues.serializers import VenueSerializer
            return VenueSerializer
        return ProfileSerializer

    def get_object(self):
        active_profile = 'user'
        if hasattr(self.request, 'auth') and self.request.auth and hasattr(self.request.auth, 'payload'):
            active_profile = self.request.auth.payload.get('active_profile', 'user')
            
        if active_profile == 'venue':
            if hasattr(self.request.user, 'venue_profile'):
                return self.request.user.venue_profile
            from rest_framework.exceptions import NotFound
            raise NotFound("Venue profile not found.")
            
        return self.request.user

    @extend_schema(summary="Get Active Profile", description="Retrieves the current authenticated user or venue profile based on active_profile.", tags=['Profile'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Update Active Profile", description="Updates the current profile (User or Venue).", tags=['Profile'])
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(summary="Partial Update Active Profile", tags=['Profile'])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

class PublicProfileView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserPublicProfileSerializer
    queryset = User.objects.filter(is_active=True)
    lookup_field = 'username'

    @extend_schema(summary="Get Public Profile", description="Retrieves the public profile of another user by username.", tags=['Profile'])
    def get(self, request, *args, **kwargs):
        # Check if the requesting user is blocked by the target user
        user = self.get_object()
        if UserBlock.objects.filter(blocker=user, blocked=request.user).exists():
            return error_response(message="You cannot view this profile.", status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(user)
        return success_response(data=serializer.data)

class FollowUserView(APIView):
    permission_classes = (IsAuthenticated, IsActiveProfileUser)

    @extend_schema(
        summary="Follow/Unfollow User", 
        description="Toggles follow status for the given username.", 
        tags=['Profile'],
        request=None,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request, username):
        if request.user.username == username:
            return error_response(message="You cannot follow yourself.", status=status.HTTP_400_BAD_REQUEST)
        
        target_user = get_object_or_404(User, username=username)
        
        # Check block status
        if UserBlock.objects.filter(blocker=target_user, blocked=request.user).exists() or \
           UserBlock.objects.filter(blocker=request.user, blocked=target_user).exists():
            return error_response(message="Cannot perform this action.", status=status.HTTP_403_FORBIDDEN)

        follow, created = UserFollow.objects.get_or_create(follower=request.user, following=target_user)
        
        if not created:
            follow.delete()
            return success_response(message="Unfollowed successfully.")
        
        return success_response(message="Followed successfully.")

class FollowersListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsActiveProfileUser)
    serializer_class = UserFollowerSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(summary="Get Followers", description="Lists the followers of the given username.", tags=['Profile'])
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return UserFollow.objects.none()
        username = self.kwargs['username']
        user = get_object_or_404(User, username=username)
        return UserFollow.objects.filter(following=user).select_related('follower')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

class FollowingListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsActiveProfileUser)
    serializer_class = UserFollowingSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(summary="Get Following", description="Lists the users the given username is following.", tags=['Profile'])
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return UserFollow.objects.none()
        username = self.kwargs['username']
        user = get_object_or_404(User, username=username)
        return UserFollow.objects.filter(follower=user).select_related('following')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

class BlockUserView(APIView):
    permission_classes = (IsAuthenticated, IsActiveProfileUser)

    @extend_schema(
        summary="Block/Unblock User", 
        description="Toggles block status for the given username.", 
        tags=['Profile'],
        request=None,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request, username):
        try:
            blocked = SocialConnectionService.toggle_block(request.user, username)
            message = "Blocked successfully." if blocked else "Unblocked successfully."
            return success_response(message=message)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)

class ReportUserView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, IsActiveProfileUser)
    serializer_class = UserReportSerializer

    @extend_schema(summary="Report User", description="Reports a user.", tags=['Profile'])
    def create(self, request, username, *args, **kwargs):
        if request.user.username == username:
            return error_response(message="You cannot report yourself.", status=status.HTTP_400_BAD_REQUEST)
        
        target_user = get_object_or_404(User, username=username)
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(reporter=request.user, reported_user=target_user)
            return success_response(message="Report submitted successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class BlockedUsersListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsActiveProfileUser)
    serializer_class = UserBlockedSerializer
    pagination_class = StandardResultsSetPagination

    @extend_schema(summary="Get Blocked Users", description="Lists the users blocked by the authenticated user.", tags=['Profile'])
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return UserBlock.objects.none()
        return UserBlock.objects.filter(blocker=self.request.user).select_related('blocked')

class UserSettingsView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSettingsSerializer

    @extend_schema(summary="Get User Settings", description="Retrieves the settings for the current user.", tags=['Settings'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Update User Settings", description="Updates the privacy and notification settings for the current user.", tags=['Settings'])
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(summary="Partial Update User Settings", tags=['Settings'])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        # Using get_or_create ensures no 404 if signal failed or for older users
        from .models import UserSettings
        settings, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return settings
