from django.urls import path, include

urlpatterns = [
    path('storage/', include('apps.storage.urls')),
    # Future apps will be included here
    path('users/', include('apps.users.urls')),
    # path('venues/', include('apps.venues.urls')),
]
