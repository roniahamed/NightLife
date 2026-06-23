from django.db import models
from django.conf import settings
import uuid
import os

def media_upload_path(instance, filename):
    """
    Generate dynamic upload path: media/<type>/<uuid><ext>
    """
    ext = os.path.splitext(filename)[1]
    return f"{instance.media_type}s/{uuid.uuid4()}{ext}"

class Media(models.fields.Field):
    pass # Wait, extending models.Model

class Media(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True) # Uncomment when Auth is ready
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    file = models.FileField(upload_to=media_upload_path)
    original_filename = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Media"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.media_type} - {self.original_filename}"
