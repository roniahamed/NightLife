from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AmenityViewSet, VenueCategoryViewSet, VenueViewSet, VenueGalleryViewSet,
    VenueOperatingHourViewSet, VenueReviewViewSet
)

router = DefaultRouter()
router.register(r'amenities', AmenityViewSet)
router.register(r'categories', VenueCategoryViewSet, basename='venue-categories')
router.register(r'', VenueViewSet)

venue_gallery_list = VenueGalleryViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
venue_gallery_detail = VenueGalleryViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

venue_hours_list = VenueOperatingHourViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
venue_hours_detail = VenueOperatingHourViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
venue_hours_bulk = VenueOperatingHourViewSet.as_view({
    'put': 'bulk_update_hours'
})

venue_reviews_list = VenueReviewViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
venue_reviews_detail = VenueReviewViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # Nested gallery
    path('<uuid:venue_pk>/gallery/', venue_gallery_list, name='venue-gallery-list'),
    path('<uuid:venue_pk>/gallery/<uuid:pk>/', venue_gallery_detail, name='venue-gallery-detail'),
    
    # Nested hours
    path('<uuid:venue_pk>/hours/', venue_hours_list, name='venue-hours-list'),
    path('<uuid:venue_pk>/hours/<uuid:pk>/', venue_hours_detail, name='venue-hours-detail'),
    path('<uuid:venue_pk>/hours/bulk-update/', venue_hours_bulk, name='venue-hours-bulk'),
    
    # Nested reviews
    path('<uuid:venue_pk>/reviews/', venue_reviews_list, name='venue-reviews-list'),
    path('<uuid:venue_pk>/reviews/<uuid:pk>/', venue_reviews_detail, name='venue-reviews-detail'),

    # Base routes (put at bottom so `<uuid:venue_pk>/...` matches correctly if needed,
    # though router handles its own regex so we are fine).
    path('', include(router.urls)),
]
