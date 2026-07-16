from django.db import models
from django.conf import settings

class FCMDevice(models.Model):
    DEVICE_TYPES = (
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web')
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fcm_devices')
    registration_id = models.CharField(max_length=255, unique=True, help_text="The FCM token for the device")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='android')
    is_active = models.BooleanField(default=True, help_text="Inactive devices won't be sent notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FCM Device"
        verbose_name_plural = "FCM Devices"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({'Active' if self.is_active else 'Inactive'})"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('system', 'System'),
        ('event_invite', 'Event Invite'),
        ('ticket_purchase', 'Ticket Purchase'),
        ('general', 'General'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    related_object_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID of related object (e.g., event ID)")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title} ({'Read' if self.is_read else 'Unread'})"
