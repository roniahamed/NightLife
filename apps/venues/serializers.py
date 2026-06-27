from rest_framework import serializers
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
    location_coordinates = serializers.SerializerMethodField()

    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    distance = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Venue
        fields = [
            'id', 'owner', 'name', 'description', 'address', 'location', 'location_coordinates',
            'latitude', 'longitude', 'distance', 'profile_image', 'cover_image', 'price_tier', 'capacity',
            'email', 'phone', 'website', 'amenities', 'amenity_ids', 'categories', 'category_ids',
            'is_active', 'is_following',
            'gallery', 'operating_hours', 'statistic', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_location_coordinates(self, obj):
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None

    def get_distance(self, obj):
        if hasattr(obj, 'distance') and obj.distance is not None:
            # Returns distance in kilometers if calculated in the viewset
            return getattr(obj.distance, 'km', obj.distance)
        return None

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return VenueFollow.objects.filter(user=request.user, venue=obj).exists()
        return False
