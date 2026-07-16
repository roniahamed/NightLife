from django.db.models import Q, Count, Sum, F, FloatField, ExpressionWrapper, Exists, OuterRef, Max
from django.db.models.functions import Coalesce
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.venues.models import Venue, VenueOperatingHour
from apps.events.models import Event

class DiscoveryService:
    @staticmethod
    def annotate_venue_card_details(queryset):
        now = timezone.now()
        local_time = timezone.localtime(now)
        current_weekday = local_time.weekday()
        current_time = local_time.time()

        is_open_subquery = VenueOperatingHour.objects.filter(
            venue=OuterRef('pk'),
            day_of_week=current_weekday,
            is_closed=False,
            open_time__lte=current_time,
            close_time__gte=current_time
        )

        return queryset.annotate(
            upcoming_events_count=Count('events', filter=Q(events__start_time__gte=now), distinct=True),
            followers_count=F('statistic__followers_count'),
            average_rating=F('statistic__average_rating'),
            is_open_now=Exists(is_open_subquery)
        ).prefetch_related('categories', 'amenities')

    @staticmethod
    def search_all(query, entity_type='all', lat=None, lng=None, radius_km=50, tags=None):
        query = query.strip()
        users, venues, events = [], [], []
        
        # Don't require a query if doing a spatial search or tag search
        if not query and not (lat and lng) and not tags:
            return [], [], []

        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D
        
        point = None
        if lat and lng:
            try:
                point = Point(float(lng), float(lat), srid=4326)
            except (ValueError, TypeError):
                pass

        if entity_type in ['all', 'people']:
            qs = User.objects.filter(is_active=True)
            if query:
                qs = qs.filter(
                    Q(username__icontains=query) | 
                    Q(first_name__icontains=query) | 
                    Q(last_name__icontains=query)
                )
            users = qs[:10]

        if entity_type in ['all', 'clubs']:
            base_venues = Venue.objects.filter(is_active=True)
            if query:
                base_venues = base_venues.filter(
                    Q(name__icontains=query) | 
                    Q(address__icontains=query) |
                    Q(description__icontains=query)
                )
            if point:
                base_venues = base_venues.filter(location__distance_lte=(point, D(km=radius_km)))
            venues = DiscoveryService.annotate_venue_card_details(base_venues)[:10]

        if entity_type in ['all', 'events']:
            base_events = Event.objects.filter(is_active=True)
            if query:
                base_events = base_events.filter(
                    Q(title__icontains=query) | 
                    Q(description__icontains=query)
                )
            if point:
                base_events = base_events.filter(venue__location__distance_lte=(point, D(km=radius_km)))
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',')]
                base_events = base_events.filter(tags__overlap=tag_list)
            events = base_events[:10]

        return users, venues, events

    @staticmethod
    def get_trending_summary(lat=None, lng=None, radius_km=50):
        now = timezone.now()
        tonight_end = now.replace(hour=23, minute=59, second=59)
        
        events_qs = Event.objects.filter(is_active=True, start_time__range=(now, tonight_end))
        
        if lat and lng:
            try:
                user_loc = Point(float(lng), float(lat), srid=4326)
                events_qs = events_qs.filter(venue__location__distance_lte=(user_loc, D(km=radius_km)))
            except (TypeError, ValueError):
                pass
                
        total_events_tonight = events_qs.count()
        
        # Calculate active people tonight (RSVPs + Tickets Sold)
        aggregated = events_qs.aggregate(
            total_rsvps=Count('rsvps'),
            total_tickets=Sum('ticket_purchases__quantity', filter=Q(ticket_purchases__status='completed'))
        )
        total_active = (aggregated['total_rsvps'] or 0) + (aggregated['total_tickets'] or 0)
        
        # Add a baseline of active platform users (simulate 10-30k for realism as per UI if needed)
        # We will just return the real DB count here.
        return {
            'total_events_tonight': total_events_tonight,
            'total_active_people': total_active
        }

    @staticmethod
    def get_heatmap_zones(lat=None, lng=None, radius_km=20, time_filter='live', min_lat=None, max_lat=None, min_lng=None, max_lng=None):
        from apps.venues.services import HeatmapService
        venues = Venue.objects.filter(is_active=True, location__isnull=False)

        # Bounding box filtering takes precedence over radius if provided
        if min_lat and max_lat and min_lng and max_lng:
            try:
                from django.contrib.gis.geos import Polygon
                bbox = Polygon.from_bbox((float(min_lng), float(min_lat), float(max_lng), float(max_lat)))
                venues = venues.filter(location__within=bbox)
            except (TypeError, ValueError):
                pass
        elif lat and lng:
            try:
                from django.contrib.gis.geos import Point
                from django.contrib.gis.measure import D
                user_location = Point(float(lng), float(lat), srid=4326)
                venues = venues.filter(location__distance_lte=(user_location, D(km=radius_km)))
            except (TypeError, ValueError):
                pass

        # Use the central optimized HeatmapService for consistency
        venues = HeatmapService.annotate_venue_with_heat_score(venues)

        # Normalize the 1000 max score to a 100% scale for the HeatmapZone API
        from django.db.models import F, FloatField, ExpressionWrapper
        venues = venues.annotate(
            heat_percentage=ExpressionWrapper(
                F('calculated_heat_score') / 10.0,
                output_field=FloatField()
            )
        ).order_by('-heat_percentage')

        return venues

    @staticmethod
    def get_heatmap_stats(lat=None, lng=None, radius_km=20, time_filter='live'):
        now = timezone.now()
        local_time = timezone.localtime(now)
        
        if time_filter == 'live':
            end_time = now + timedelta(hours=4)
        elif time_filter == 'tonight':
            end_time = now.replace(hour=23, minute=59, second=59)
        else: # this week
            end_time = now + timedelta(days=7)

        venues = Venue.objects.filter(is_active=True, location__isnull=False)
        events = Event.objects.filter(is_active=True, start_time__range=(now, end_time))

        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                venues = venues.filter(location__distance_lte=(user_location, D(km=radius_km)))
                events = events.filter(venue__location__distance_lte=(user_location, D(km=radius_km)))
            except (TypeError, ValueError):
                pass

        # Active Now = RSVPs + Tickets for events in window
        agg_events = events.aggregate(
            total_rsvps=Count('rsvps'),
            total_tickets=Sum('ticket_purchases__quantity', filter=Q(ticket_purchases__status='completed'))
        )
        active_now = (agg_events['total_rsvps'] or 0) + (agg_events['total_tickets'] or 0)

        # Hot Events = Events with > 10 RSVPs or tickets
        hot_events = events.annotate(
            interest=Count('rsvps') + Coalesce(Sum('ticket_purchases__quantity'), 0)
        ).filter(interest__gte=10).count()

        # Clubs Open
        is_open_subquery = VenueOperatingHour.objects.filter(
            venue=OuterRef('pk'),
            day_of_week=local_time.weekday(),
            is_closed=False,
            open_time__lte=local_time.time(),
            close_time__gte=local_time.time()
        )
        clubs_open = venues.annotate(is_open=Exists(is_open_subquery)).filter(is_open=True).count()

        # Heat Zones (arbitrary definition: venues with high activity)
        # We can just count venues that have at least 1 upcoming event in the window
        heat_zones = venues.filter(events__start_time__range=(now, end_time)).distinct().count()

        return {
            'active_now': active_now,
            'hot_events': hot_events,
            'clubs_open': clubs_open,
            'heat_zones': heat_zones
        }

    @staticmethod
    def get_trending_venues(user=None, limit=5):
        from apps.venues.services import HeatmapService
        from apps.venues.models import VenueFollow
        qs = Venue.objects.filter(is_active=True, is_approved=True)
        qs = HeatmapService.annotate_venue_with_heat_score(qs)
        
        # Filter out venues the user is already following if user is provided
        if user and user.is_authenticated:
            following_ids = VenueFollow.objects.filter(user=user).values_list('venue_id', flat=True)
            qs = qs.exclude(id__in=following_ids)
            
        # Sort by the dynamically calculated heat score and select top X
        return qs.order_by('-calculated_heat_score')[:limit]

    @staticmethod
    def get_trending():
        venues = DiscoveryService.get_trending_venues(limit=10)

        events = Event.objects.filter(is_active=True).annotate(
            rsvp_count=Count('rsvps'),
            trending_score=Count('rsvps') * 1.5
        ).order_by('-trending_score')[:10]

        return venues, events

    @staticmethod
    def get_nearby_venues(lat, lng, radius_km=5):
        try:
            user_location = Point(float(lng), float(lat), srid=4326)
        except (TypeError, ValueError):
            return Venue.objects.none()

        venues = Venue.objects.filter(
            is_active=True, location__isnull=False
        ).annotate(
            distance=Distance('location', user_location)
        ).filter(
            distance__lte=D(km=radius_km)
        ).order_by('distance')[:20]

        return venues
