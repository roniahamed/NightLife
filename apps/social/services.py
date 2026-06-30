from django.db import transaction
from django.utils import timezone
from .models import Post, PostMedia, PostMention, Comment, Like, SavedPost, Story
from apps.users.models import User
from apps.venues.models import Venue

class SocialService:
    @staticmethod
    @transaction.atomic
    def create_post(user, caption, media_files=None, visibility='public', tags=None, location_venue_id=None, location_coordinates=None, event_id=None, mentions=None):
        venue_profile = None
        if hasattr(user, 'venue_profile') and getattr(user, 'registration_type', 'user') == 'venue':
            venue_profile = user.venue_profile
            
        post = Post.objects.create(
            author=user,
            venue_profile=venue_profile,
            event_id=event_id,
            caption=caption,
            visibility=visibility,
            tags=tags if tags else [],
            location_venue_id=location_venue_id,
            location_coordinates=location_coordinates
        )
        
        if media_files:
            for index, file in enumerate(media_files):
                # Simple logic to determine if it's a video based on extension
                media_type = 'video' if str(file).lower().endswith(('.mp4', '.mov', '.avi')) else 'image'
                PostMedia.objects.create(post=post, file=file, media_type=media_type, order=index)
                
        if mentions:
            for user_id in mentions:
                try:
                    mentioned_user = User.objects.get(id=user_id)
                    PostMention.objects.create(post=post, user=mentioned_user)
                except User.DoesNotExist:
                    pass
                    
        return post

    @staticmethod
    def toggle_like(user, post_id):
        post = Post.objects.get(id=post_id)
        like, created = Like.objects.get_or_create(post=post, user=user)
        if not created:
            like.delete()
            return False # Unliked
        return True # Liked
        
    @staticmethod
    def add_comment(user, post_id, text, parent_id=None):
        post = Post.objects.get(id=post_id)
        comment = Comment.objects.create(post=post, user=user, text=text, parent_id=parent_id)
        return comment
        
    @staticmethod
    def toggle_save_post(user, post_id):
        post = Post.objects.get(id=post_id)
        saved, created = SavedPost.objects.get_or_create(post=post, user=user)
        if not created:
            saved.delete()
            return False # Unsaved
        return True # Saved

    @staticmethod
    def create_story(user, media, expires_in_hours=24):
        venue_profile = None
        if hasattr(user, 'venue_profile') and getattr(user, 'registration_type', 'user') == 'venue':
            venue_profile = user.venue_profile
            
        media_type = 'video' if str(media).lower().endswith(('.mp4', '.mov', '.avi')) else 'image'
        expires_at = timezone.now() + timezone.timedelta(hours=expires_in_hours)
        
        story = Story.objects.create(
            author=user,
            venue_profile=venue_profile,
            media=media,
            media_type=media_type,
            expires_at=expires_at
        )
        return story
