from django.contrib import admin
from .models import Venue, VenueCategory, Amenity, VenueGallery, VenueOperatingHour, VenueReview

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'owner', 'is_approved', 'is_active', 'created_at')
    list_filter = ('is_approved', 'is_active', 'created_at')
    search_fields = ('name', 'username', 'owner__email', 'owner__username')
    actions = ['approve_venues', 'disapprove_venues']

    def approve_venues(self, request, queryset):
        queryset.update(is_approved=True)
    approve_venues.short_description = "Approve selected venues"

    def disapprove_venues(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_venues.short_description = "Disapprove selected venues"

@admin.register(VenueCategory)
class VenueCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(VenueGallery)
class VenueGalleryAdmin(admin.ModelAdmin):
    list_display = ('venue', 'caption', 'order', 'created_at')
    list_filter = ('venue',)

@admin.register(VenueOperatingHour)
class VenueOperatingHourAdmin(admin.ModelAdmin):
    list_display = ('venue', 'day_of_week', 'open_time', 'close_time', 'is_closed')
    list_filter = ('venue', 'day_of_week', 'is_closed')

@admin.register(VenueReview)
class VenueReviewAdmin(admin.ModelAdmin):
    list_display = ('venue', 'user', 'rating', 'created_at')
    list_filter = ('venue', 'rating', 'created_at')
    search_fields = ('venue__name', 'user__email', 'user__username')
