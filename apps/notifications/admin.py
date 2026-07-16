from django.contrib import admin
from .models import Notification, FCMDevice

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('created_at',)


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('device_type', 'is_active')
    search_fields = ('user__email', 'registration_id')
