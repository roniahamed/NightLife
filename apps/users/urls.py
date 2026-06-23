from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, VerifyOTPView, ResendOTPView, ForgotPasswordView, 
    VerifyResetOTPView, ResetPasswordView, ChangePasswordView, ProfileView
)

urlpatterns = [
    # Auth Endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    
    # Standard JWT Login
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password Management
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('password/verify-reset-otp/', VerifyResetOTPView.as_view(), name='verify-reset-otp'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset-password'),
    path('password/change/', ChangePasswordView.as_view(), name='change-password'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
]
