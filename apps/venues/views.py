from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

from .models import Venue, Amenity, VenueCategory, VenueGallery, VenueOperatingHour, VenueReview
from .serializers import (
    VenueSerializer, AmenitySerializer, VenueCategorySerializer, VenueGallerySerializer,
    VenueOperatingHourSerializer, VenueReviewSerializer
)
from . import services

class VenueCategoryViewSet(viewsets.ModelViewSet):
    queryset = VenueCategory.objects.all()
    serializer_class = VenueCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class AmenityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for amenities.
    Admins will manage amenities via the Django admin or a separate endpoint.
    """
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Venue.objects.all()
        
        lat = self.request.query_params.get('latitude')
        lng = self.request.query_params.get('longitude')
        
        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                queryset = queryset.annotate(distance=Distance('location', user_location)).order_by('distance')
            except ValueError:
                pass
                
        return queryset

    def perform_create(self, serializer):
        active_profile = self.request.auth.payload.get('active_profile') if hasattr(self.request, 'auth') and self.request.auth else self.request.user.registration_type
        if active_profile != 'venue':
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You must switch to your venue profile to create a venue.")
        
        if hasattr(self.request.user, 'venue_profile'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You already have a venue profile.")
            
        venue = services.create_venue(
            owner=self.request.user,
            **serializer.validated_data
        )
        serializer.instance = venue

    def perform_update(self, serializer):
        if serializer.instance.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to edit this venue.")
            
        venue = services.update_venue(
            serializer.instance,
            **serializer.validated_data
        )
        serializer.instance = venue

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        services.increment_venue_view(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        venue = self.get_object()
        services.follow_venue(request.user, venue)
        return Response({"status": "following venue"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        venue = self.get_object()
        services.unfollow_venue(request.user, venue)
        return Response({"status": "unfollowed venue"}, status=status.HTTP_200_OK)


class VenueGalleryViewSet(viewsets.ModelViewSet):
    serializer_class = VenueGallerySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return VenueGallery.objects.filter(venue_id=self.kwargs['venue_pk'])

    def perform_create(self, serializer):
        venue = Venue.objects.get(pk=self.kwargs['venue_pk'])
        services.add_venue_gallery_image(
            venue=venue,
            image=serializer.validated_data['image'],
            caption=serializer.validated_data.get('caption', ''),
            order=serializer.validated_data.get('order', 0)
        )


class VenueOperatingHourViewSet(viewsets.ModelViewSet):
    serializer_class = VenueOperatingHourSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return VenueOperatingHour.objects.filter(venue_id=self.kwargs['venue_pk'])

    def perform_create(self, serializer):
        # We can still use the service for bulk setting, but this endpoint might just set one.
        # Alternatively, we could create a custom action on VenueViewSet for bulk setting hours.
        venue = Venue.objects.get(pk=self.kwargs['venue_pk'])
        serializer.save(venue=venue)

    @action(detail=False, methods=['put'], url_path='bulk-update')
    def bulk_update_hours(self, request, venue_pk=None):
        venue = Venue.objects.get(pk=venue_pk)
        hours_data = request.data # Expects a list
        services.set_operating_hours(venue, hours_data)
        return Response({"status": "hours updated"}, status=status.HTTP_200_OK)


class VenueReviewViewSet(viewsets.ModelViewSet):
    serializer_class = VenueReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return VenueReview.objects.filter(venue_id=self.kwargs['venue_pk'])

    def perform_create(self, serializer):
        venue = Venue.objects.get(pk=self.kwargs['venue_pk'])
        review = services.add_venue_review(
            venue=venue,
            user=self.request.user,
            rating=serializer.validated_data['rating'],
            comment=serializer.validated_data.get('comment', '')
        )
        serializer.instance = review
