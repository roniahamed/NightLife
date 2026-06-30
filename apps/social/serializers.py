from rest_framework import serializers
from .models import Post, PostMedia, PostMention, Comment, Like, SavedPost, Story
from apps.users.serializers import UserPublicProfileSerializer
from apps.venues.serializers import VenueSerializer
from apps.events.serializers import EventSerializer

class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'file', 'media_type', 'order']

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
            'id', 'author', 'venue_profile', 'event', 'caption', 'visibility', 'tags',
            'location_venue', 'location_coordinates', 'media', 'mentions',
            'likes_count', 'comments_count', 'shares_count', 'is_liked', 'is_saved', 'recent_comments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'venue_profile', 'created_at', 'updated_at']

    def get_recent_comments(self, obj):
        # Return the 3 most recent top-level comments
        comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')[:3]
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_likes_count(self, obj) -> int:
        return obj.likes.count()

    def get_comments_count(self, obj) -> int:
        return obj.comments.count()

    def get_is_liked(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_is_saved(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPost.objects.filter(post=obj, user=request.user).exists()
        return False

class StorySerializer(serializers.ModelSerializer):
    author = UserPublicProfileSerializer(read_only=True)
    
    class Meta:
        model = Story
        fields = ['id', 'author', 'venue_profile', 'media', 'media_type', 'expires_at', 'created_at']
        read_only_fields = ['author', 'venue_profile', 'expires_at', 'created_at']
