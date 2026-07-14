from django.db import transaction
from django.utils import timezone
from .models import Post, PostMedia, PostMention, Comment, Like, SavedPost, Story
from apps.users.models import User
from apps.venues.models import Venue

class SocialService:
    @staticmethod
    @transaction.atomic
    def create_post(user, caption, mood=None, media_files=None, visibility='public', tags=None, location_venue_id=None, location_coordinates=None, event_id=None, mentions=None, active_profile='user'):
        from rest_framework.exceptions import ValidationError
        from apps.events.models import Event
        from apps.venues.models import Venue

        venue_profile = None
        if hasattr(user, 'venue_profile') and active_profile == 'venue':
            venue_profile = user.venue_profile
        else:
            # For general users, enforce that they tag either a venue or an event.
            if active_profile == 'user':
                if not location_venue_id and not event_id:
                    raise ValidationError("General users must tag either an event or a venue to create a post.")
        
        # Validate foreign keys to avoid IntegrityError
        if event_id and not Event.objects.filter(id=event_id).exists():
            raise ValidationError("The specified event does not exist.")
        if location_venue_id and not Venue.objects.filter(id=location_venue_id).exists():
            raise ValidationError("The specified venue does not exist.")
            
        post = Post.objects.create(
            author=user,
            venue_profile=venue_profile,
            event_id=event_id,
            caption=caption,
            mood=mood,
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
    def create_story(user, media, expires_in_hours=24, active_profile='user'):
        venue_profile = None
        if hasattr(user, 'venue_profile') and active_profile == 'venue':
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
