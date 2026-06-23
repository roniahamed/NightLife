from rest_framework import serializers
from .models import Media
from .validators import get_validator_for_type

class MediaUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'media_type', 'file', 'original_filename', 'size_bytes', 'created_at']
        read_only_fields = ['id', 'original_filename', 'size_bytes', 'created_at']

    def validate(self, attrs):
        media_type = attrs.get('media_type')
        file = attrs.get('file')

        validator = get_validator_for_type(media_type)
        if not validator:
            raise serializers.ValidationError({"media_type": "Invalid media type."})
        
        # Run specific validation
        validator(file)
        
        return attrs

    def create(self, validated_data):
        file = validated_data.get('file')
        validated_data['original_filename'] = file.name
        validated_data['size_bytes'] = file.size
        # Add user from request once authentication is implemented
        # request = self.context.get('request')
        # if request and request.user.is_authenticated:
        #     validated_data['user'] = request.user
        
        return super().create(validated_data)
