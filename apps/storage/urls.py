from django.urls import path
from .views import MediaUploadView

urlpatterns = [
    path('upload/', MediaUploadView.as_view(), name='media-upload'),
]
