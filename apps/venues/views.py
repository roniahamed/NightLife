from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

from .models import Venue, Amenity, VenueCategory, VenueGallery, VenueOperatingHour, VenueReview
from .serializers import (
    VenueSerializer, AmenitySerializer, VenueCategorySerializer, VenueGallerySerializer,
    VenueOperatingHourSerializer, VenueReviewSerializer
)
from . import services
import stripe
from django.conf import settings
from rest_framework.views import APIView
from apps.common.permissions import IsActiveProfileVenue
from apps.common.utils import success_response, error_response
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.types import OpenApiTypes

stripe.api_key = settings.STRIPE_SECRET_KEY

@extend_schema_view(
    list=extend_schema(tags=['Venue Category & Amenities']),
    retrieve=extend_schema(tags=['Venue Category & Amenities']),
    create=extend_schema(tags=['Venue Category & Amenities']),
    update=extend_schema(tags=['Venue Category & Amenities']),
    partial_update=extend_schema(tags=['Venue Category & Amenities']),
    destroy=extend_schema(tags=['Venue Category & Amenities']),
)
class VenueCategoryViewSet(viewsets.ModelViewSet):
    queryset = VenueCategory.objects.all()
    serializer_class = VenueCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

@extend_schema_view(
    list=extend_schema(tags=['Venue Category & Amenities']),
    retrieve=extend_schema(tags=['Venue Category & Amenities']),
)
class AmenityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for amenities.
    Admins will manage amenities via the Django admin or a separate endpoint.
    """
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema_view(
    list=extend_schema(tags=['Venues']),
    retrieve=extend_schema(tags=['Venues']),
    create=extend_schema(tags=['Venues']),
    update=extend_schema(tags=['Venues']),
    partial_update=extend_schema(tags=['Venues']),
    destroy=extend_schema(tags=['Venues']),
    follow=extend_schema(tags=['Venues']),
    unfollow=extend_schema(tags=['Venues']),
)
class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        from django.db.models import Q
        
        # Base filter: only show approved and active venues
        # unless user is admin or the owner of the unapproved venue
        if self.request.user and self.request.user.is_staff:
            queryset = Venue.objects.all()
        elif self.request.user and self.request.user.is_authenticated:
            queryset = Venue.objects.filter(
                Q(is_approved=True, is_active=True) | Q(owner=self.request.user)
            )
        else:
            queryset = Venue.objects.filter(is_approved=True, is_active=True)
        
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


@extend_schema_view(
    list=extend_schema(tags=['Venue Details']),
    retrieve=extend_schema(tags=['Venue Details']),
    create=extend_schema(tags=['Venue Details']),
    update=extend_schema(tags=['Venue Details']),
    partial_update=extend_schema(tags=['Venue Details']),
    destroy=extend_schema(tags=['Venue Details']),
)
class VenueGalleryViewSet(viewsets.ModelViewSet):
    serializer_class = VenueGallerySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VenueGallery.objects.none()
        return VenueGallery.objects.filter(venue_id=self.kwargs['venue_pk'])

    def perform_create(self, serializer):
        venue = Venue.objects.get(pk=self.kwargs['venue_pk'])
        services.add_venue_gallery_image(
            venue=venue,
            image=serializer.validated_data['image'],
            caption=serializer.validated_data.get('caption', ''),
            order=serializer.validated_data.get('order', 0)
        )


@extend_schema_view(
    list=extend_schema(tags=['Venue Details']),
    retrieve=extend_schema(tags=['Venue Details']),
    create=extend_schema(tags=['Venue Details']),
    update=extend_schema(tags=['Venue Details']),
    partial_update=extend_schema(tags=['Venue Details']),
    destroy=extend_schema(tags=['Venue Details']),
    bulk_update_hours=extend_schema(tags=['Venue Details']),
)
class VenueOperatingHourViewSet(viewsets.ModelViewSet):
    serializer_class = VenueOperatingHourSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VenueOperatingHour.objects.none()
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


@extend_schema_view(
    list=extend_schema(tags=['Venue Details']),
    retrieve=extend_schema(tags=['Venue Details']),
    create=extend_schema(tags=['Venue Details']),
    update=extend_schema(tags=['Venue Details']),
    partial_update=extend_schema(tags=['Venue Details']),
    destroy=extend_schema(tags=['Venue Details']),
)
class VenueReviewViewSet(viewsets.ModelViewSet):
    serializer_class = VenueReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VenueReview.objects.none()
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

class VenueStripeOnboardingView(APIView):
    permission_classes = [IsAuthenticated, IsActiveProfileVenue]

    @extend_schema(summary="Stripe Onboarding", description="Generates Stripe Connect onboarding URL.", request=None, responses={200: OpenApiTypes.OBJECT}, tags=['Venue Payments'])
    def post(self, request):
        user = request.user
        if not hasattr(user, 'venue_profile'):
            return error_response(message="You do not have a venue profile.", status=status.HTTP_400_BAD_REQUEST)
            
        venue = user.venue_profile
        
        try:
            # Create Stripe Account if not exists
            if not venue.stripe_account_id:
                account = stripe.Account.create(
                    type="express",
                    email=venue.owner.email,
                    business_type="company",
                    company={"name": venue.name},
                )
                venue.stripe_account_id = account.id
                venue.save()
            
            # Create Account Link
            account_link = stripe.AccountLink.create(
                account=venue.stripe_account_id,
                refresh_url=request.build_absolute_uri('/api/venues/stripe/onboard/refresh/'),
                return_url=request.build_absolute_uri('/api/venues/stripe/onboard/return/'),
                type="account_onboarding",
            )
            
            return success_response(data={"url": account_link.url})
        except Exception as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)

class VenueStripeOnboardingReturnView(APIView):
    permission_classes = [IsAuthenticated, IsActiveProfileVenue]

    @extend_schema(summary="Stripe Onboarding Return", description="Handles return from Stripe Connect onboarding.", request=None, responses={200: OpenApiTypes.OBJECT}, tags=['Venue Payments'])
    def get(self, request):
        user = request.user
        venue = getattr(user, 'venue_profile', None)
        if not venue or not venue.stripe_account_id:
            return error_response(message="Invalid venue or Stripe account.", status=status.HTTP_400_BAD_REQUEST)
            
        try:
            account = stripe.Account.retrieve(venue.stripe_account_id)
            if account.details_submitted:
                # Release held funds
                from apps.events.models import TicketPurchase
                held_purchases = TicketPurchase.objects.filter(
                    event__venue=venue, 
                    status='completed', 
                    funds_transferred_to_venue=False
                )
                
                total_transferred = 0
                for purchase in held_purchases:
                    amount_to_transfer = purchase.total_amount - purchase.platform_fee
                    if amount_to_transfer > 0:
                        stripe.Transfer.create(
                            amount=int(amount_to_transfer * 100),
                            currency='usd',
                            destination=venue.stripe_account_id,
                            metadata={'purchase_id': str(purchase.id)}
                        )
                    purchase.funds_transferred_to_venue = True
                    purchase.save()
                    total_transferred += amount_to_transfer
                    
                return success_response(message=f"Onboarding successful. Released ${total_transferred} in held funds.")
            else:
                return error_response(message="Stripe onboarding not completed.", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
