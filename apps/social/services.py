from django.db import transaction
from django.db.models import Count, Prefetch
from django.utils import timezone
from .models import Post, PostMedia, PostMention, Comment, Like, SavedPost, Story
from apps.users.models import User
from apps.venues.models import Venue
from .utils import generate_thumbnail

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
                media_obj = PostMedia.objects.create(post=post, file=file, media_type=media_type, order=index)
                
                # Generate thumbnail
                thumbnail_file = generate_thumbnail(media_obj.file, media_type)
                if thumbnail_file:
                    media_obj.thumbnail.save(thumbnail_file.name, thumbnail_file, save=True)
                
                
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
    def create_story(user, media=None, text_content=None, bg_color=None, expires_in_hours=24, active_profile='user'):
        venue_profile = None
        if hasattr(user, 'venue_profile') and active_profile == 'venue':
            venue_profile = user.venue_profile
            
        if media:
            media_type = 'video' if str(media).lower().endswith(('.mp4', '.mov', '.avi')) else 'image'
        else:
            media_type = 'text'
            
        expires_at = timezone.now() + timezone.timedelta(hours=expires_in_hours)
        
        story = Story.objects.create(
            author=user,
            venue_profile=venue_profile,
            media=media,
            text_content=text_content,
            bg_color=bg_color,
            media_type=media_type,
            expires_at=expires_at
        )
        
        # Generate thumbnail
        if media:
            thumbnail_file = generate_thumbnail(story.media, media_type)
            if thumbnail_file:
                story.thumbnail.save(thumbnail_file.name, thumbnail_file, save=True)
            
        return story

    @staticmethod
    def group_stories(queryset):
        grouped_stories = {}
        
        for story in queryset:
            key = f"venue_{story.venue_profile.id}" if story.venue_profile else f"user_{story.author.id}"
            if key not in grouped_stories:
                grouped_stories[key] = {
                    "user": getattr(story.author, 'public_profile', None) if not story.venue_profile else None,
                    "venue": story.venue_profile,
                    "stories": []
                }
            grouped_stories[key]["stories"].append(story)
            
        formatted_data = []
        for key, data in grouped_stories.items():
            formatted_data.append({
                "user": data["stories"][0].author if not data["venue"] else None,
                "venue": data["venue"],
                "stories": data["stories"]
            })
            
        return formatted_data

    @staticmethod
    def _annotate_user_status(qs, user):
        from django.db.models import Exists, OuterRef
        from apps.social.models import Like, SavedPost
        from apps.venues.models import VenueFollow
        
        if hasattr(user, 'is_authenticated') and user.is_authenticated:
            qs = qs.annotate(
                is_liked_annotated=Exists(Like.objects.filter(post=OuterRef('pk'), user=user)),
                is_saved_annotated=Exists(SavedPost.objects.filter(post=OuterRef('pk'), user=user)),
                is_following_venue_annotated=Exists(VenueFollow.objects.filter(venue=OuterRef('venue_profile_id'), user=user))
            )
        return qs

    @staticmethod
    def get_for_you_feed(user):
        qs = Post.objects.filter(
            venue_profile__isnull=False
        ).select_related(
            'author', 'venue_profile'
        ).prefetch_related(
            'media', 'mentions'
        ).annotate(
            likes_count_annotated=Count('likes', distinct=True),
            comments_count_annotated=Count('comments', distinct=True)
        )
        
        qs = SocialService._annotate_user_status(qs, user)

        # Prefetch recent comments to avoid N+1 queries in the serializer
        recent_comments_qs = Comment.objects.filter(parent__isnull=True).order_by('-created_at')
        qs = qs.prefetch_related(
            Prefetch('comments', queryset=recent_comments_qs, to_attr='prefetched_recent_comments')
        )

        # Apply preference: if user follows venues, prioritize them
        followed_venue_ids = []
        if hasattr(user, 'venue_follows'):
            followed_venue_ids = list(user.venue_follows.values_list('venue_id', flat=True))
            
        from django.db.models import Case, When, Value, IntegerField
        
        qs = qs.annotate(
            priority=Case(
                When(venue_profile_id__in=followed_venue_ids, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
                
        # Order by priority (highest first), then latest created, then id
        return qs.order_by('-priority', '-created_at', '-id')

    @staticmethod
    def get_following_feed(user):
        followed_venue_ids = []
        if hasattr(user, 'venue_follows'):
            followed_venue_ids = list(user.venue_follows.values_list('venue_id', flat=True))
            
        qs = Post.objects.filter(
            venue_profile_id__in=followed_venue_ids
        ).select_related(
            'author', 'venue_profile'
        ).prefetch_related(
            'media', 'mentions'
        ).annotate(
            likes_count_annotated=Count('likes', distinct=True),
            comments_count_annotated=Count('comments', distinct=True)
        )
        
        qs = SocialService._annotate_user_status(qs, user)

        recent_comments_qs = Comment.objects.filter(parent__isnull=True).order_by('-created_at')
        qs = qs.prefetch_related(
            Prefetch('comments', queryset=recent_comments_qs, to_attr='prefetched_recent_comments')
        )
        
        return qs.order_by('-created_at')

    @staticmethod
    def get_nearby_feed(user, latitude=None, longitude=None):
        from django.contrib.gis.geos import Point
        from django.contrib.gis.db.models.functions import Distance
        from django.db.models import Value, FloatField

        qs = Post.objects.filter(venue_profile__isnull=False)

        point = None
        if latitude and longitude:
            try:
                point = Point(float(longitude), float(latitude), srid=4326)
            except (ValueError, TypeError):
                pass
        
        if not point and hasattr(user, 'location') and user.location:
            point = user.location
            
        if point:
            qs = qs.annotate(distance=Distance('venue_profile__location', point))
        else:
            qs = qs.annotate(distance=Value(0.0, output_field=FloatField()))

        qs = qs.select_related(
            'author', 'venue_profile'
        ).prefetch_related(
            'media', 'mentions'
        ).annotate(
            likes_count_annotated=Count('likes', distinct=True),
            comments_count_annotated=Count('comments', distinct=True)
        )
        
        qs = SocialService._annotate_user_status(qs, user)

        recent_comments_qs = Comment.objects.filter(parent__isnull=True).order_by('-created_at')
        qs = qs.prefetch_related(
            Prefetch('comments', queryset=recent_comments_qs, to_attr='prefetched_recent_comments')
        )
        
        return qs.order_by('distance', '-created_at', 'id')
