import re

with open('apps/users/views.py', 'r') as f:
    content = f.read()

# Add imports
content = content.replace("from .services import UserProfileService", "from .services import UserProfileService, AuthService, SocialConnectionService")

# Remove generate_and_send_otp
content = re.sub(r'def generate_and_send_otp.*?class RegisterView', 'class RegisterView', content, flags=re.DOTALL)

# RegisterView
content = content.replace("generate_and_send_otp(user, otp_type='register')", "AuthService.generate_and_send_otp(user, otp_type='register')")

# VerifyOTPView
verify_otp_old = """        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response(message="User not found.", status=status.HTTP_404_NOT_FOUND)
            
        otp_record = UserOTP.objects.filter(user=user, otp_type='register', is_used=False).order_by('-created_at').first()
        
        if not otp_record or not otp_record.is_valid():
            return error_response(message="OTP expired or not found.", status=status.HTTP_400_BAD_REQUEST)
            
        if check_password(otp, otp_record.otp_hash):
            otp_record.is_used = True
            otp_record.save()
            
            user.is_email_verified = True
            user.is_active = True
            user.save()
            
            refresh = RefreshToken.for_user(user)
            return success_response(
                data={
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                message="Email verified and logged in successfully.",
                status=status.HTTP_200_OK
            )
        else:
            return error_response(message="Invalid OTP.", status=status.HTTP_400_BAD_REQUEST)"""
verify_otp_new = """        try:
            token_data = AuthService.verify_registration_otp(email, otp)
            return success_response(
                data=token_data,
                message="Email verified and logged in successfully.",
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            if str(e) == "User not found.":
                return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)"""
content = content.replace(verify_otp_old, verify_otp_new)

# ResendOTPView
resend_otp_old = """            try:
                user = User.objects.get(email=serializer.validated_data['email'])
            except User.DoesNotExist:
                return error_response(message="User not found.", status=status.HTTP_404_NOT_FOUND)
            
            if user.is_active:
                return error_response(message="Account is already verified and active.", status=status.HTTP_400_BAD_REQUEST)
                
            generate_and_send_otp(user, otp_type='register')
            return success_response(message="A new OTP has been sent to your email.")"""
resend_otp_new = """            try:
                AuthService.resend_registration_otp(serializer.validated_data['email'])
                return success_response(message="A new OTP has been sent to your email.")
            except ValueError as e:
                if str(e) == "User not found.":
                    return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)"""
content = content.replace(resend_otp_old, resend_otp_new)

# ForgotPasswordView
forgot_otp_old = """            try:
                user = User.objects.get(email=serializer.validated_data['email'])
                generate_and_send_otp(user, otp_type='reset')
                return success_response(message="If an account exists, an OTP was sent.")
            except User.DoesNotExist:
                return success_response(message="If an account exists, an OTP was sent.")"""
forgot_otp_new = """            AuthService.request_password_reset_otp(serializer.validated_data['email'])
            return success_response(message="If an account exists, an OTP was sent.")"""
content = content.replace(forgot_otp_old, forgot_otp_new)

# VerifyResetOTPView
verify_reset_old = """            try:
                user = User.objects.get(email=serializer.validated_data['email'])
            except User.DoesNotExist:
                return error_response(message="User not found.", status=status.HTTP_404_NOT_FOUND)
                
            otp_record = UserOTP.objects.filter(user=user, otp_type='reset', is_used=False).order_by('-created_at').first()
            if not otp_record or not otp_record.is_valid():
                return error_response(message="OTP expired or not found.", status=status.HTTP_400_BAD_REQUEST)
                
            if check_password(serializer.validated_data['otp'], otp_record.otp_hash):
                otp_record.is_used = True
                otp_record.save()
                
                # Generate token
                token = default_token_generator.make_token(user)
                
                return success_response(
                    data={"token": token},
                    message="OTP verified. Use this token and your email to reset password."
                )
            else:
                return error_response(message="Invalid OTP.", status=status.HTTP_400_BAD_REQUEST)"""
verify_reset_new = """            try:
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
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)"""
content = content.replace(verify_reset_old, verify_reset_new)

# ResetPasswordView
reset_pass_old = """            try:
                user = User.objects.get(email=serializer.validated_data['email'])
            except User.DoesNotExist:
                return error_response(message="User not found.", status=status.HTTP_404_NOT_FOUND)
                
            if default_token_generator.check_token(user, serializer.validated_data['token']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return success_response(message="Password reset successfully.")
            else:
                return error_response(message="Invalid or expired token.", status=status.HTTP_400_BAD_REQUEST)"""
reset_pass_new = """            try:
                AuthService.reset_password_with_token(
                    serializer.validated_data['email'],
                    serializer.validated_data['token'],
                    serializer.validated_data['new_password']
                )
                return success_response(message="Password reset successfully.")
            except ValueError as e:
                if str(e) == "User not found.":
                    return error_response(message=str(e), status=status.HTTP_404_NOT_FOUND)
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)"""
content = content.replace(reset_pass_old, reset_pass_new)

# ChangePasswordView
change_pass_old = """            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return error_response(message="Incorrect old password.", status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return success_response(message="Password changed successfully.")"""
change_pass_new = """            try:
                AuthService.change_password(
                    request.user,
                    serializer.validated_data['old_password'],
                    serializer.validated_data['new_password']
                )
                return success_response(message="Password changed successfully.")
            except ValueError as e:
                return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)"""
content = content.replace(change_pass_old, change_pass_new)

# FollowUserView
follow_old = """        if request.user.username == username:
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
        
        return success_response(message="Followed successfully.")"""
follow_new = """        from rest_framework.exceptions import PermissionDenied
        try:
            followed = SocialConnectionService.toggle_follow(request.user, username)
            message = "Followed successfully." if followed else "Unfollowed successfully."
            return success_response(message=message)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return error_response(message=str(e), status=status.HTTP_403_FORBIDDEN)"""
content = content.replace(follow_old, follow_new)

# BlockUserView
block_old = """        if request.user.username == username:
            return error_response(message="You cannot block yourself.", status=status.HTTP_400_BAD_REQUEST)
        
        target_user = get_object_or_404(User, username=username)

        block, created = UserBlock.objects.get_or_create(blocker=request.user, blocked=target_user)
        
        if not created:
            block.delete()
            return success_response(message="Unblocked successfully.")
        
        # If blocked, also unfollow each other
        UserFollow.objects.filter(follower=request.user, following=target_user).delete()
        UserFollow.objects.filter(follower=target_user, following=request.user).delete()

        return success_response(message="Blocked successfully.")"""
block_new = """        try:
            blocked = SocialConnectionService.toggle_block(request.user, username)
            message = "Blocked successfully." if blocked else "Unblocked successfully."
            return success_response(message=message)
        except ValueError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)"""
content = content.replace(block_old, block_new)

with open('apps/users/views.py', 'w') as f:
    f.write(content)
