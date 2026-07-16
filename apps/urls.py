from django.urls import path, include

urlpatterns = [
    path('storage/', include('apps.storage.urls')),
    # Future apps will be included here
    path('common/', include('apps.common.urls')),
    path('users/', include('apps.users.urls')),
    path('venues/', include('apps.venues.urls')),
    path('events/', include('apps.events.urls')),
    path('discovery/', include('apps.discovery.urls')),
    path('social/', include('apps.social.urls')),
    path('tickets/', include('apps.tickets.urls')),
    path('notifications/', include('apps.notifications.urls')),
]
