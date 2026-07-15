from rest_framework import viewsets, permissions, status, mixins, generics
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample
from rest_framework.response import Response
from django.utils import timezone
from .models import Post, Comment, Story
from .serializers import PostSerializer, CommentSerializer, StorySerializer, PostCreateSerializer, StoryCreateSerializer, StoryFeedGroupSerializer
from .services import SocialService
from apps.common.pagination import StandardResultsSetPagination, CursorSetPagination
from apps.common.permissions import IsOwnerOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

@extend_schema_view(
    list=extend_schema(tags=['Social Posts']),
    retrieve=extend_schema(tags=['Social Posts']),
    update=extend_schema(tags=['Social Posts']),
    partial_update=extend_schema(tags=['Social Posts']),
    destroy=extend_schema(tags=['Social Posts']),
)
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related('author').prefetch_related('media', 'mentions', 'likes', 'comments')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['author', 'venue_profile']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter for venue feed if requested
        is_venue_feed = self.request.query_params.get('venue_feed', 'false').lower() == 'true'
        if is_venue_feed:
            queryset = queryset.filter(venue_profile__isnull=False)
            
        return queryset.order_by('-created_at')

    @extend_schema(
        summary="Create a new social post",
        request=PostCreateSerializer,
        responses={201: PostSerializer},
        tags=['Social Posts']
    )
    def create(self, request, *args, **kwargs):
        caption = request.data.get('caption', '')
        mood = request.data.get('mood')
        visibility = request.data.get('visibility', 'public')
        tags = request.data.getlist('tags') if hasattr(request.data, 'getlist') else request.data.get('tags', [])
        location_venue_id = request.data.get('venue')
        event_id = request.data.get('event')
        mentions = request.data.getlist('mentions') if hasattr(request.data, 'getlist') else request.data.get('mentions', [])
        media_files = request.FILES.getlist('media')

        active_profile = request.auth.payload.get('active_profile', 'user') if hasattr(request, 'auth') and request.auth else getattr(request.user, 'registration_type', 'user')

        post = SocialService.create_post(
            user=request.user,
            active_profile=active_profile,
            caption=caption,
            mood=mood,
            media_files=media_files,
            visibility=visibility,
            tags=tags,
            location_venue_id=location_venue_id,
            event_id=event_id,
            mentions=mentions
        )
        serializer = self.get_serializer(post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Like or Unlike a Post", request=None, responses={200: OpenApiTypes.OBJECT}, tags=['Social Actions'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        liked = SocialService.toggle_like(request.user, pk)
        status_msg = 'liked' if liked else 'unliked'
        return Response({'status': status_msg})

    @extend_schema(summary="Save or Unsave a Post", request=None, responses={200: OpenApiTypes.OBJECT}, tags=['Social Actions'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def save_post(self, request, pk=None):
        saved = SocialService.toggle_save_post(request.user, pk)
        status_msg = 'saved' if saved else 'unsaved'
        return Response({'status': status_msg})

    @extend_schema(summary="Share a Post", request=None, responses={200: OpenApiTypes.OBJECT}, tags=['Social Actions'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def share(self, request, pk=None):
        post = self.get_object()
        post.shares_count += 1
        post.save(update_fields=['shares_count'])
        return Response({'status': 'shared', 'shares_count': post.shares_count})

@extend_schema_view(
    list=extend_schema(tags=['Social Comments']),
    retrieve=extend_schema(tags=['Social Comments']),
    create=extend_schema(tags=['Social Comments']),
    update=extend_schema(tags=['Social Comments']),
    partial_update=extend_schema(tags=['Social Comments']),
    destroy=extend_schema(tags=['Social Comments']),
)
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

@extend_schema_view(
    list=extend_schema(
        tags=['Social Stories'],
        responses={200: StoryFeedGroupSerializer(many=True)},
        summary="List grouped active stories"
    ),
    retrieve=extend_schema(tags=['Social Stories']),
    destroy=extend_schema(tags=['Social Stories']),
)
class StoryViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['author', 'venue_profile']

    def get_queryset(self):
        # Only return active stories
        return Story.objects.filter(expires_at__gt=timezone.now()).select_related('author', 'venue_profile').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        formatted_data = SocialService.group_stories(queryset)
        serializer = StoryFeedGroupSerializer(formatted_data, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @extend_schema(
        summary="Create a new story",
        request=StoryCreateSerializer,
        responses={201: StorySerializer},
        tags=['Social Stories']
    )
    def create(self, request, *args, **kwargs):
        serializer = StoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        media = request.FILES.get('media')
        text_content = serializer.validated_data.get('text_content')
        bg_color = serializer.validated_data.get('bg_color')
        
        active_profile = request.auth.payload.get('active_profile', 'user') if hasattr(request, 'auth') and request.auth else getattr(request.user, 'registration_type', 'user')
        
        story = SocialService.create_story(
            request.user, 
            media=media, 
            text_content=text_content, 
            bg_color=bg_color, 
            active_profile=active_profile
        )
        serializer = self.get_serializer(story)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ForYouFeedView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CursorSetPagination

    @extend_schema(
        summary="Get For You Feed",
        description="Returns an optimized, cursor-paginated feed of venue posts based on user preferences.",
        responses={200: PostSerializer(many=True)},
        parameters=[
            OpenApiParameter(name='cursor', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='The pagination cursor value.'),
        ],
        tags=['Social Posts']
    )
    def get_queryset(self):
        return SocialService.get_for_you_feed(self.request.user)

