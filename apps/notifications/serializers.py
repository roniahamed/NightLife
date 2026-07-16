from rest_framework import serializers
from .models import Notification, FCMDevice

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'related_object_id', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['registration_id', 'device_type', 'is_active']

    def create(self, validated_data):
        user = self.context['request'].user
        registration_id = validated_data.get('registration_id')
        
        # Check if the token already exists
        device, created = FCMDevice.objects.get_or_create(
            registration_id=registration_id,
            defaults={'user': user, 'device_type': validated_data.get('device_type', 'android')}
        )
        
        # If it exists but belongs to another user, update the user
        if not created:
            if device.user != user:
                device.user = user
            device.is_active = True
            device.save()
            
        return device
