from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.gis.geos import Point
from .models import UserFollow, UserBlock, UserReport, UserSettings

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'dob', 'password', 'confirm_password')
        
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        # Generate username from email
        username = validated_data['email'].split('@')[0]
        
        user = User.objects.create(
            username=username,
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            dob=validated_data.get('dob'),
            is_active=False, # Inactive until OTP is verified
            is_email_verified=False
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=4)

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class VerifyResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=4)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

class ProfileSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'dob', 'bio', 'profile_image', 'cover_image', 'location_name', 'followers_count', 'following_count', 'latitude', 'longitude', 'lat', 'lng')
        read_only_fields = ('id', 'username', 'email', 'followers_count', 'following_count')

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_lat(self, obj):
        if obj.location:
            return obj.location.y
        return None

    def get_lng(self, obj):
        if obj.location:
            return obj.location.x
        return None

    def update(self, instance, validated_data):
        lat = validated_data.pop('latitude', None)
        lng = validated_data.pop('longitude', None)
        
        if lat is not None and lng is not None:
            # Point(x, y) = Point(longitude, latitude)
            instance.location = Point(lng, lat, srid=4326)
            
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class UserPublicProfileSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'bio', 'profile_image', 'cover_image', 'location_name', 'followers_count', 'following_count', 'is_following', 'lat', 'lng')

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFollow.objects.filter(follower=request.user, following=obj).exists()
        return False

    def get_lat(self, obj):
        if obj.location:
            return obj.location.y
        return None

    def get_lng(self, obj):
        if obj.location:
            return obj.location.x
        return None

class UserFollowerSerializer(serializers.ModelSerializer):
    follower_id = serializers.UUIDField(source='follower.id')
    follower_username = serializers.CharField(source='follower.username')
    follower_first_name = serializers.CharField(source='follower.first_name')
    follower_last_name = serializers.CharField(source='follower.last_name')
    follower_profile_image = serializers.ImageField(source='follower.profile_image', read_only=True)

    class Meta:
        model = UserFollow
        fields = ('follower_id', 'follower_username', 'follower_first_name', 'follower_last_name', 'follower_profile_image', 'created_at')

class UserFollowingSerializer(serializers.ModelSerializer):
    following_id = serializers.UUIDField(source='following.id')
    following_username = serializers.CharField(source='following.username')
    following_first_name = serializers.CharField(source='following.first_name')
    following_last_name = serializers.CharField(source='following.last_name')
    following_profile_image = serializers.ImageField(source='following.profile_image', read_only=True)

    class Meta:
        model = UserFollow
        fields = ('following_id', 'following_username', 'following_first_name', 'following_last_name', 'following_profile_image', 'created_at')

class UserBlockedSerializer(serializers.ModelSerializer):
    blocked_id = serializers.UUIDField(source='blocked.id')
    blocked_username = serializers.CharField(source='blocked.username')
    blocked_first_name = serializers.CharField(source='blocked.first_name')
    blocked_last_name = serializers.CharField(source='blocked.last_name')
    blocked_profile_image = serializers.ImageField(source='blocked.profile_image', read_only=True)

    class Meta:
        model = UserBlock
        fields = ('blocked_id', 'blocked_username', 'blocked_first_name', 'blocked_last_name', 'blocked_profile_image', 'created_at')

class UserReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReport
        fields = ('id', 'reported_user', 'reason', 'description', 'created_at')
        read_only_fields = ('id', 'created_at', 'reported_user')

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        exclude = ('id', 'user')
