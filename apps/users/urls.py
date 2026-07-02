from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, VerifyOTPView, ResendOTPView, ForgotPasswordView, 
    VerifyResetOTPView, ResetPasswordView, ChangePasswordView, ProfileView,
    PublicProfileView, FollowUserView, FollowersListView, FollowingListView,
    BlockUserView, ReportUserView, BlockedUsersListView, UserSettingsView,
    CustomTokenObtainPairView, SwitchProfileView, AvailableProfilesView
)

urlpatterns = [
    # Auth Endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    
    # Standard JWT Login
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('switch-profile/', SwitchProfileView.as_view(), name='switch-profile'),
    path('available-profiles/', AvailableProfilesView.as_view(), name='available-profiles'),
    
    # Password Management
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('password/verify-reset-otp/', VerifyResetOTPView.as_view(), name='verify-reset-otp'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset-password'),
    path('password/change/', ChangePasswordView.as_view(), name='change-password'),
    
    # Profile & Settings
    path('profile/', ProfileView.as_view(), name='profile'),
    path('settings/', UserSettingsView.as_view(), name='user-settings'),
    path('<str:username>/profile/', PublicProfileView.as_view(), name='public-profile'),
    
    # Follow
    path('<str:username>/follow/', FollowUserView.as_view(), name='follow-user'),
    path('<str:username>/followers/', FollowersListView.as_view(), name='followers-list'),
    path('<str:username>/following/', FollowingListView.as_view(), name='following-list'),
    
    # Moderation
    path('blocks/', BlockedUsersListView.as_view(), name='blocked-users-list'),
    path('<str:username>/block/', BlockUserView.as_view(), name='block-user'),
    path('<str:username>/report/', ReportUserView.as_view(), name='report-user'),
]
