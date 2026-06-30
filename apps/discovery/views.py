from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from .services import DiscoveryService
from .serializers import (
    SearchUserSerializer, DiscoverVenueSerializer, SearchEventSerializer,
    TrendingVenueSerializer, TrendingEventSerializer,
    NearbyVenueSerializer, HeatmapZoneSerializer, HeatmapStatsSerializer,
    TrendingSummarySerializer
)

class GlobalSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Global Search", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        query = request.query_params.get('q', '')
        entity_type = request.query_params.get('type', 'all').lower()

        users, venues, events = DiscoveryService.search_all(query, entity_type)

        response_data = {}
        if entity_type in ['all', 'people']:
            response_data["users"] = SearchUserSerializer(users, many=True, context={'request': request}).data
        if entity_type in ['all', 'clubs']:
            response_data["venues"] = DiscoverVenueSerializer(venues, many=True, context={'request': request}).data
        if entity_type in ['all', 'events']:
            response_data["events"] = SearchEventSerializer(events, many=True, context={'request': request}).data

        return Response(response_data)

class TrendingSummaryView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Trending Summary", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        summary = DiscoveryService.get_trending_summary(lat, lng)
        return Response(TrendingSummarySerializer(summary).data)

class TrendingView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Trending Venues and Events", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        venues, events = DiscoveryService.get_trending()
        return Response({
            "venues": TrendingVenueSerializer(venues, many=True, context={'request': request}).data,
            "events": TrendingEventSerializer(events, many=True, context={'request': request}).data
        })

class HeatmapStatsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Heatmap Statistics", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 20)
        time_filter = request.query_params.get('time_filter', 'live')
        
        stats = DiscoveryService.get_heatmap_stats(lat, lng, radius, time_filter)
        return Response(HeatmapStatsSerializer(stats).data)

class HeatmapZoneView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Heatmap Zones", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 20)
        
        min_lat = request.query_params.get('min_lat')
        max_lat = request.query_params.get('max_lat')
        min_lng = request.query_params.get('min_lng')
        max_lng = request.query_params.get('max_lng')
        
        time_filter = request.query_params.get('time_filter', 'live')
        
        zones = DiscoveryService.get_heatmap_zones(
            lat=lat, lng=lng, radius_km=radius, 
            time_filter=time_filter,
            min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng
        )
        return Response({
            "zones": HeatmapZoneSerializer(zones, many=True, context={'request': request}).data
        })

class NearbyView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Nearby Venues", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 5)

        if not lat or not lng:
            return Response({"error": "Latitude (lat) and Longitude (lng) are required parameters."}, status=400)

        venues = DiscoveryService.get_nearby_venues(lat, lng, radius)
        return Response({
            "venues": NearbyVenueSerializer(venues, many=True, context={'request': request}).data
        })
