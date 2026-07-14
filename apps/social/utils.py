import os
import subprocess
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile

def generate_thumbnail(file_field, media_type):
    """
    Generates a thumbnail for a given Django FileField (which must be saved on disk).
    Returns a ContentFile containing the thumbnail JPEG data, or None if failed.
    """
    if not file_field or not hasattr(file_field, 'path') or not os.path.exists(file_field.path):
        return None

    file_path = file_field.path
    thumb_io = BytesIO()

    try:
        if media_type == 'image':
            with Image.open(file_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                img.save(thumb_io, format='JPEG', quality=85)
                return ContentFile(thumb_io.getvalue(), name=f"thumb_{os.path.basename(file_path)}.jpg")
                
        elif media_type == 'video':
            command = [
                'ffmpeg',
                '-i', file_path,
                '-ss', '00:00:00.500',
                '-vframes', '1',
                '-f', 'image2',
                '-vcodec', 'mjpeg',
                '-an',
                'pipe:1'
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode == 0 and out:
                img = Image.open(BytesIO(out))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                img.save(thumb_io, format='JPEG', quality=85)
                return ContentFile(thumb_io.getvalue(), name=f"thumb_{os.path.basename(file_path)}.jpg")
            else:
                print("FFmpeg error:", err)
                return None
                
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
        return None
        
    return None
