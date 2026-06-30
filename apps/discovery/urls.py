from django.urls import path
from .views import (
    GlobalSearchView, TrendingView, TrendingSummaryView, 
    HeatmapZoneView, HeatmapStatsView, NearbyView
)

app_name = 'discovery'

urlpatterns = [
    path('search/', GlobalSearchView.as_view(), name='search'),
    path('trending/', TrendingView.as_view(), name='trending'),
    path('trending/summary/', TrendingSummaryView.as_view(), name='trending_summary'),
    path('heatmap/zones/', HeatmapZoneView.as_view(), name='heatmap_zones'),
    path('heatmap/stats/', HeatmapStatsView.as_view(), name='heatmap_stats'),
    path('nearby/', NearbyView.as_view(), name='nearby'),
]
