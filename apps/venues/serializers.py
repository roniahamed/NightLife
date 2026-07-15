from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Venue, Amenity, VenueGallery, VenueOperatingHour, VenueReview, VenueStatistic, VenueCategory, VenueFollow

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'description', 'icon', 'created_at', 'updated_at']

class VenueCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueCategory
        fields = ['id', 'name', 'created_at']

class VenueGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueGallery
        fields = ['id', 'venue', 'image', 'caption', 'order', 'created_at']
        read_only_fields = ['id', 'venue', 'created_at']

class VenueOperatingHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueOperatingHour
        fields = ['id', 'venue', 'day_of_week', 'open_time', 'close_time', 'is_closed']
        read_only_fields = ['id', 'venue']

class VenueReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = VenueReview
        fields = ['id', 'venue', 'user', 'user_name', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'venue', 'user', 'created_at', 'updated_at']

class VenueStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueStatistic
        fields = ['total_views', 'total_reviews', 'average_rating', 'favorites_count', 'followers_count', 'heat_score']

class VenueSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    categories = VenueCategorySerializer(many=True, read_only=True)
    gallery = VenueGallerySerializer(many=True, read_only=True)
    operating_hours = VenueOperatingHourSerializer(many=True, read_only=True)
    statistic = VenueStatisticSerializer(read_only=True)
    is_following = serializers.SerializerMethodField(read_only=True)
    is_stripe_connected = serializers.SerializerMethodField(read_only=True)
    post_count = serializers.SerializerMethodField(read_only=True)
    events_count = serializers.SerializerMethodField(read_only=True)
    followers_count = serializers.SerializerMethodField(read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    heat_score = serializers.SerializerMethodField(read_only=True)
    
    amenity_ids = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        source='amenities',
        many=True,
        write_only=True,
        required=False
    )
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=VenueCategory.objects.all(),
        source='categories',
        many=True,
        write_only=True,
        required=False
    )
    
    # Simple GeoJSON representation for location if available
    location = serializers.CharField(read_only=True)
    location_coordinates = serializers.SerializerMethodField()

    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    distance = serializers.SerializerMethodField(read_only=True)

    registration_type = serializers.CharField(source='owner.registration_type', read_only=True)
    is_user_profile_active = serializers.BooleanField(source='owner.is_user_profile_active', read_only=True)

    class Meta:
        model = Venue
        fields = [
            'id', 'owner', 'username', 'name', 'description', 'address', 'location', 'location_coordinates',
            'latitude', 'longitude', 'distance', 'profile_image', 'cover_image', 'price_tier', 'capacity',
            'email', 'phone', 'website', 'amenities', 'amenity_ids', 'categories', 'category_ids',
            'is_active', 'is_following', 'is_stripe_connected',
            'post_count', 'events_count', 'followers_count', 'average_rating', 'heat_score',
            'gallery', 'operating_hours', 'statistic', 'created_at', 'updated_at',
            'registration_type', 'is_user_profile_active'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'registration_type', 'is_user_profile_active', 'post_count', 'events_count', 'followers_count', 'average_rating', 'heat_score']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self, 'partial', False) and hasattr(self, 'initial_data'):
            from django.http import QueryDict
            if isinstance(self.initial_data, QueryDict):
                self.initial_data = self.initial_data.copy()
            
            if type(self.initial_data) is dict or isinstance(self.initial_data, QueryDict):
                keys_to_remove = [k for k, v in self.initial_data.items() if v == '' and k not in ['description']]
                for k in keys_to_remove:
                    self.initial_data.pop(k)

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_location_coordinates(self, obj):
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance(self, obj):
        if hasattr(obj, 'distance') and obj.distance is not None:
            # Returns distance in kilometers if calculated in the viewset
            return getattr(obj.distance, 'km', obj.distance)
        return None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(user=request.user).exists()
        return False
        
    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_stripe_connected(self, obj):
        return bool(obj.stripe_account_id)

    @extend_schema_field(OpenApiTypes.INT)
    def get_post_count(self, obj):
        return obj.venue_posts.count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_events_count(self, obj):
        return obj.events.count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_followers_count(self, obj):
        return obj.followers.count()

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_average_rating(self, obj):
        if hasattr(obj, 'statistic') and obj.statistic:
            return float(obj.statistic.average_rating)
        return 0.0

    @extend_schema_field(OpenApiTypes.INT)
    def get_heat_score(self, obj):
        if hasattr(obj, 'statistic') and obj.statistic:
            return obj.statistic.heat_score
        return 0

class DashboardChartDataSerializer(serializers.Serializer):
    day = serializers.CharField()
    revenue = serializers.FloatField()

class DashboardRecentActivitySerializer(serializers.Serializer):
    type = serializers.CharField()
    message = serializers.CharField()
    time = serializers.DateTimeField()
    icon = serializers.CharField()

class DashboardAnalyticsSerializer(serializers.Serializer):
    revenue_this_week = serializers.FloatField()
    revenue_percentage_change = serializers.FloatField()
    total_followers = serializers.IntegerField()
    new_followers_this_week = serializers.IntegerField()
    tickets_sold_this_week = serializers.IntegerField()
    tickets_sold_percentage_change = serializers.FloatField()
    heat_score = serializers.IntegerField()
    revenue_chart_data = DashboardChartDataSerializer(many=True)
    recent_activity = DashboardRecentActivitySerializer(many=True)
    
    total_tickets_sold = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    platform_fees_paid = serializers.FloatField()
    net_earnings = serializers.FloatField()
    stripe_available_balance = serializers.FloatField()
    stripe_pending_balance = serializers.FloatField()
    active_events_count = serializers.IntegerField()
    recent_transactions = serializers.ListField(child=serializers.DictField())
