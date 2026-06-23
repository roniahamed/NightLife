import os
from django.core.exceptions import ValidationError
from django.conf import settings

def validate_image(file):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(file.name)[1].lower()
    
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed extensions are jpg, jpeg, png, gif, webp.')
    
    limit = getattr(settings, 'MAX_IMAGE_SIZE_MB', 5) * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f'File size exceeds the limit of {settings.MAX_IMAGE_SIZE_MB}MB.')

def validate_video(file):
    valid_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    ext = os.path.splitext(file.name)[1].lower()
    
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed extensions are mp4, mov, avi, mkv.')
    
    limit = getattr(settings, 'MAX_VIDEO_SIZE_MB', 50) * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f'File size exceeds the limit of {settings.MAX_VIDEO_SIZE_MB}MB.')

def validate_document(file):
    valid_extensions = ['.pdf', '.doc', '.docx', '.txt']
    ext = os.path.splitext(file.name)[1].lower()
    
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed extensions are pdf, doc, docx, txt.')
    
    limit = getattr(settings, 'MAX_DOCUMENT_SIZE_MB', 10) * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f'File size exceeds the limit of {settings.MAX_DOCUMENT_SIZE_MB}MB.')

def get_validator_for_type(media_type):
    validators = {
        'image': validate_image,
        'video': validate_video,
        'document': validate_document
    }
    return validators.get(media_type)
