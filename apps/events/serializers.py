from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import EventCategory, Event, EventRSVP, EventTicketTier, TicketPurchase, EventLineup

class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ['id', 'name', 'created_at']

class EventRSVPSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_profile_image = serializers.ImageField(source='user.profile_image', read_only=True)
    
    class Meta:
        model = EventRSVP
        fields = ['id', 'event', 'user', 'user_name', 'user_profile_image', 'status', 'created_at']
        read_only_fields = ['id', 'event', 'user', 'created_at']

class EventTicketTierSerializer(serializers.ModelSerializer):
    available_quantity = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = EventTicketTier
        fields = ['id', 'event', 'name', 'price', 'total_quantity', 'sold_quantity', 'available_quantity', 'description', 'created_at']
        read_only_fields = ['id', 'event', 'sold_quantity', 'created_at']
        
    @extend_schema_field(OpenApiTypes.INT)
    def get_available_quantity(self, obj):
        from django.db.models import Sum
        from django.utils import timezone
        from datetime import timedelta
        
        active_pending_quantity = TicketPurchase.objects.filter(
            ticket_tier=obj,
            status='pending',
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        available = obj.total_quantity - obj.sold_quantity - active_pending_quantity
        return max(0, available)

class EventLineupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLineup
        fields = ['id', 'event', 'artist_name', 'artist_image', 'role', 'created_at']
        read_only_fields = ['id', 'event', 'created_at']

class TicketPurchaseSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    ticket_tier_name = serializers.CharField(source='ticket_tier.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = TicketPurchase
        fields = [
            'id', 'user', 'user_email', 'event', 'event_title', 'ticket_tier', 
            'ticket_tier_name', 'quantity', 'total_amount', 'platform_fee', 
            'status', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'event', 'ticket_tier', 'total_amount', 
            'platform_fee', 'status', 'created_at'
        ]

class EventSerializer(serializers.ModelSerializer):
    categories = EventCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=EventCategory.objects.all(),
        source='categories',
        many=True,
        write_only=True,
        required=False
    )
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_image = serializers.ImageField(source='venue.profile_image', read_only=True)
    ticket_tiers = EventTicketTierSerializer(many=True, read_only=True)
    lineup = EventLineupSerializer(many=True, read_only=True)
    rsvp_count = serializers.SerializerMethodField(read_only=True)
    user_rsvp_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'venue', 'venue_name', 'venue_image', 'title', 'description', 
            'start_time', 'end_time', 'cover_image', 'ticket_price', 'ticket_url',
            'ticket_tiers', 'lineup', 'capacity', 'custom_venue_address', 'dress_code',
            'age_restriction', 'categories', 'category_ids', 'tags', 'is_active', 
            'rsvp_count', 'user_rsvp_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'venue', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.INT)
    def get_rsvp_count(self, obj):
        return obj.rsvps.filter(status='going').count()

    @extend_schema_field(OpenApiTypes.STR)
    def get_user_rsvp_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rsvp = EventRSVP.objects.get(user=request.user, event=obj)
                return rsvp.status
            except EventRSVP.DoesNotExist:
                return None
        return None
