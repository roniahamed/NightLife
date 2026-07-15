from rest_framework import serializers
from .models import Post, PostMedia, PostMention, Comment, Like, SavedPost, Story
from apps.users.serializers import UserPublicProfileSerializer
from apps.venues.serializers import VenueSerializer
from apps.events.serializers import EventSerializer
from apps.venues.models import VenueFollow

class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'file', 'thumbnail', 'media_type', 'order']

class PostMentionSerializer(serializers.ModelSerializer):
    user = UserPublicProfileSerializer(read_only=True)
    class Meta:
        model = PostMention
        fields = ['id', 'user']

class CommentSerializer(serializers.ModelSerializer):
    user = UserPublicProfileSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'parent', 'created_at', 'updated_at', 'replies_count']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_replies_count(self, obj) -> int:
        return obj.replies.count()

class PostSerializer(serializers.ModelSerializer):
    author = UserPublicProfileSerializer(read_only=True)
    venue_profile = VenueSerializer(read_only=True)
    location_venue = VenueSerializer(read_only=True)
    media = PostMediaSerializer(many=True, read_only=True)
    mentions = PostMentionSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    recent_comments = serializers.SerializerMethodField()
    # Handle GeoDjango PointField explicitly to avoid spectacular errors
    location_coordinates = serializers.CharField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'venue_profile', 'event', 'caption', 'mood', 'visibility', 'tags',
            'location_venue', 'location_coordinates', 'media', 'mentions',
            'likes_count', 'comments_count', 'shares_count', 'is_liked', 'is_saved', 'recent_comments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'venue_profile', 'created_at', 'updated_at']

    def get_recent_comments(self, obj):
        # Use prefetched recent comments if available, else query DB
        if hasattr(obj, 'prefetched_recent_comments'):
            comments = obj.prefetched_recent_comments
        else:
            comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')[:3]
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_likes_count(self, obj) -> int:
        if hasattr(obj, 'likes_count_annotated'):
            return obj.likes_count_annotated
        return obj.likes.count()

    def get_comments_count(self, obj) -> int:
        if hasattr(obj, 'comments_count_annotated'):
            return obj.comments_count_annotated
        return obj.comments.count()

    def get_is_liked(self, obj) -> bool:
        if hasattr(obj, 'is_liked_annotated'):
            return obj.is_liked_annotated
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_is_saved(self, obj) -> bool:
        if hasattr(obj, 'is_saved_annotated'):
            return obj.is_saved_annotated
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPost.objects.filter(post=obj, user=request.user).exists()
        return False

class StorySerializer(serializers.ModelSerializer):
    author = UserPublicProfileSerializer(read_only=True)
    
    class Meta:
        model = Story
        fields = ['id', 'author', 'venue_profile', 'media', 'text_content', 'bg_color', 'thumbnail', 'media_type', 'expires_at', 'created_at']
        read_only_fields = ['author', 'venue_profile', 'expires_at', 'created_at']

class StoryFeedGroupSerializer(serializers.Serializer):
    user = UserPublicProfileSerializer(required=False, allow_null=True)
    venue = VenueSerializer(required=False, allow_null=True)
    stories = StorySerializer(many=True)

class PostCreateSerializer(serializers.Serializer):
    caption = serializers.CharField(required=False, allow_blank=True)
    mood = serializers.CharField(required=False, max_length=10)
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES, default='public')
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
    venue = serializers.UUIDField(required=False, help_text="Venue ID. General users must provide either venue or event.")
    event = serializers.UUIDField(required=False, help_text="Event ID. General users must provide either venue or event.")
    mentions = serializers.ListField(child=serializers.UUIDField(), required=False)
    media = serializers.ListField(child=serializers.FileField(), required=False)

class StoryCreateSerializer(serializers.Serializer):
    media = serializers.FileField(required=False)
    text_content = serializers.CharField(required=False)
    bg_color = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        if not data.get('media') and not data.get('text_content'):
            raise serializers.ValidationError("Either media or text_content must be provided.")
        return data

class FeedPostSerializer(serializers.ModelSerializer):
    media = PostMediaSerializer(many=True, read_only=True)
    mentions = PostMentionSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    recent_comments = serializers.SerializerMethodField()
    
    venue_username = serializers.SerializerMethodField()
    venue_name = serializers.SerializerMethodField()
    is_following_venue = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    profile_id = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'caption', 'tags', 'media', 'mentions',
            'profile_id', 'profile_pic', 'venue_username', 'venue_name', 'is_following_venue', 
            'location_name', 'location_coordinates', 'distance',
            'likes_count', 'comments_count', 'shares_count', 'is_liked', 'is_saved', 'recent_comments', 
            'created_at', 'updated_at'
        ]

    from drf_spectacular.utils import extend_schema_field
    from drf_spectacular.types import OpenApiTypes

    @extend_schema_field(CommentSerializer(many=True))
    def get_recent_comments(self, obj):
        if hasattr(obj, 'prefetched_recent_comments'):
            comments = obj.prefetched_recent_comments[:5]
        else:
            comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')[:5]
        return CommentSerializer(comments, many=True, context=self.context).data

    @extend_schema_field(OpenApiTypes.INT)
    def get_likes_count(self, obj) -> int:
        return obj.likes_count_annotated if hasattr(obj, 'likes_count_annotated') else obj.likes.count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_comments_count(self, obj) -> int:
        return obj.comments_count_annotated if hasattr(obj, 'comments_count_annotated') else obj.comments.count()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_liked(self, obj) -> bool:
        if hasattr(obj, 'is_liked_annotated'):
            return obj.is_liked_annotated
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_saved(self, obj) -> bool:
        if hasattr(obj, 'is_saved_annotated'):
            return obj.is_saved_annotated
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPost.objects.filter(post=obj, user=request.user).exists()
        return False

    @extend_schema_field(OpenApiTypes.STR)
    def get_venue_username(self, obj):
        return obj.venue_profile.username if obj.venue_profile and obj.venue_profile.username else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_venue_name(self, obj):
        return obj.venue_profile.name if obj.venue_profile else None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_following_venue(self, obj) -> bool:
        if hasattr(obj, 'is_following_venue_annotated'):
            return obj.is_following_venue_annotated
        req = self.context.get('request')
        if not req or not req.user.is_authenticated or not obj.venue_profile:
            return False
        return VenueFollow.objects.filter(user=req.user, venue=obj.venue_profile).exists()
        
    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance(self, obj):
        if hasattr(obj, 'distance'):
            # Convert Distance object to km if applicable
            return getattr(obj.distance, 'km', obj.distance) if hasattr(obj.distance, 'km') else obj.distance
        return None

    @extend_schema_field(OpenApiTypes.UUID)
    def get_profile_id(self, obj):
        if obj.venue_profile:
            return obj.venue_profile.id
        elif obj.author:
            return obj.author.id
        return None

    @extend_schema_field(OpenApiTypes.URI)
    def get_profile_pic(self, obj):
        request = self.context.get('request')
        image = None
        if obj.venue_profile and obj.venue_profile.profile_image:
            image = obj.venue_profile.profile_image
        elif obj.author and getattr(obj.author, 'profile_image', None):
            image = obj.author.profile_image
            
        if image:
            return request.build_absolute_uri(image.url) if request else image.url
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_location_name(self, obj):
        if obj.location_venue:
            return obj.location_venue.name
        if obj.venue_profile:
            return obj.venue_profile.address
        return None
