from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Media
from .serializers import MediaUploadSerializer
from apps.common.utils import success_response, error_response
from drf_spectacular.utils import extend_schema

class MediaUploadView(generics.CreateAPIView):
    queryset = Media.objects.all()
    serializer_class = MediaUploadSerializer
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        summary="Upload Media File",
        description="Upload an image, video, or document. Enforces size constraints and allowed extensions.",
        request=MediaUploadSerializer,
        responses={201: MediaUploadSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return success_response(
                data=serializer.data, 
                message="File uploaded successfully", 
                status=status.HTTP_201_CREATED
            )
        return error_response(
            errors=serializer.errors,
            message="File upload failed",
            status=status.HTTP_400_BAD_REQUEST
        )
