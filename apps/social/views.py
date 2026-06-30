from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Post, Comment, Story
from .serializers import PostSerializer, CommentSerializer, StorySerializer
from .services import SocialService
from apps.common.pagination import StandardResultsSetPagination

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related('author').prefetch_related('media', 'mentions', 'likes', 'comments')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter for venue feed if requested
        is_venue_feed = self.request.query_params.get('venue_feed', 'false').lower() == 'true'
        if is_venue_feed:
            queryset = queryset.filter(venue_profile__isnull=False)
            
        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        caption = request.data.get('caption', '')
        visibility = request.data.get('visibility', 'public')
        tags = request.data.getlist('tags') if hasattr(request.data, 'getlist') else request.data.get('tags', [])
        location_venue_id = request.data.get('location_venue')
        event_id = request.data.get('event')
        mentions = request.data.getlist('mentions') if hasattr(request.data, 'getlist') else request.data.get('mentions', [])
        media_files = request.FILES.getlist('media')

        post = SocialService.create_post(
            user=request.user,
            caption=caption,
            media_files=media_files,
            visibility=visibility,
            tags=tags,
            location_venue_id=location_venue_id,
            event_id=event_id,
            mentions=mentions
        )
        serializer = self.get_serializer(post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        liked = SocialService.toggle_like(request.user, pk)
        status_msg = 'liked' if liked else 'unliked'
        return Response({'status': status_msg})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def save_post(self, request, pk=None):
        saved = SocialService.toggle_save_post(request.user, pk)
        status_msg = 'saved' if saved else 'unsaved'
        return Response({'status': status_msg})

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        post_id = self.kwargs.get('post_pk')
        if post_id:
            return Comment.objects.filter(post_id=post_id, parent__isnull=True).select_related('user').order_by('-created_at')
        return Comment.objects.none()

    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_pk')
        serializer.save(user=self.request.user, post_id=post_id)

class StoryViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Only return active stories
        return Story.objects.filter(expires_at__gt=timezone.now()).select_related('author').order_by('-created_at')

    def create(self, request, *args, **kwargs):
        media = request.FILES.get('media')
        if not media:
            return Response({'error': 'Media file is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        story = SocialService.create_story(request.user, media)
        serializer = self.get_serializer(story)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
