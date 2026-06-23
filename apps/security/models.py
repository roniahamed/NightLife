from django.db import models
from django.conf import settings
import uuid

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True) # Enable after Phase 5
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    status_code = models.PositiveIntegerField()
    execution_time_ms = models.FloatField(help_text="Execution time in milliseconds")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['status_code']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code} ({self.execution_time_ms}ms)"
