from rest_framework import serializers
from apps.users.models import User
from apps.venues.models import Venue
from apps.events.models import Event

class SearchUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_image']

from apps.venues.serializers import VenueGallerySerializer, AmenitySerializer

class DiscoverVenueSerializer(serializers.ModelSerializer):
    rating = serializers.FloatField(source='average_rating', read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    upcoming_events_count = serializers.IntegerField(read_only=True)
    is_open_now = serializers.BooleanField(read_only=True)
    categories = serializers.StringRelatedField(many=True)
    price_tier_display = serializers.CharField(source='get_price_tier_display', read_only=True)
    
    gallery = VenueGallerySerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    upcoming_events = serializers.SerializerMethodField()
    social_posts = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'address', 'profile_image', 'cover_image', 
            'price_tier_display', 'capacity', 'rating', 'followers_count', 
            'upcoming_events_count', 'is_open_now', 'categories',
            'gallery', 'amenities', 'upcoming_events', 'social_posts'
        ]

    def get_upcoming_events(self, obj):
        from django.utils import timezone
        from apps.events.serializers import EventSerializer
        events = obj.events.filter(start_time__gte=timezone.now()).order_by('start_time')[:3]
        return EventSerializer(events, many=True, context=self.context).data

    def get_social_posts(self, obj):
        from apps.social.serializers import PostSerializer
        posts = obj.venue_posts.order_by('-created_at')[:3]
        return PostSerializer(posts, many=True, context=self.context).data

class SearchEventSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 'start_time', 'cover_image', 'venue_name']

class TrendingVenueSerializer(serializers.ModelSerializer):
    heat_score = serializers.FloatField(source='trending_score', read_only=True)
    followers_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'profile_image', 'heat_score', 'followers_count']

class TrendingEventSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    rsvp_count = serializers.IntegerField(read_only=True)
    trending_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 'start_time', 'cover_image', 'venue_name', 'rsvp_count', 'trending_score']

class NearbyVenueSerializer(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'profile_image', 'distance', 'lat', 'lng']

    def get_distance(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lng(self, obj):
        return obj.location.x if obj.location else None

class HeatmapZoneSerializer(serializers.ModelSerializer):
    heat_percentage = serializers.FloatField(read_only=True)
    heat_level = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = ['id', 'name', 'lat', 'lng', 'heat_percentage', 'heat_level']

    def get_heat_level(self, obj):
        percentage = getattr(obj, 'heat_percentage', 0)
        if percentage >= 85: return 'Insane'
        if percentage >= 65: return 'Hot'
        if percentage >= 40: return 'Active'
        return 'Mild'

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lng(self, obj):
        return obj.location.x if obj.location else None

class HeatmapStatsSerializer(serializers.Serializer):
    active_now = serializers.IntegerField()
    hot_events = serializers.IntegerField()
    clubs_open = serializers.IntegerField()
    heat_zones = serializers.IntegerField()
    
class TrendingSummarySerializer(serializers.Serializer):
    total_events_tonight = serializers.IntegerField()
    total_active_people = serializers.IntegerField()
