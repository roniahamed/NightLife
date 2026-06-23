from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
import random

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, blank=False, null=False)
    is_email_verified = models.BooleanField(default=False)
    
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    dob = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='cover_images/', null=True, blank=True)
    
    # GeoDjango PostGIS PointField & Name
    location = gis_models.PointField(null=True, blank=True, srid=4326)
    location_name = models.CharField(max_length=255, blank=True)
    
    # Require email for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class UserOTP(models.Model):
    OTP_TYPES = (
        ('register', 'Registration'),
        ('reset', 'Password Reset')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_type = models.CharField(max_length=20, choices=OTP_TYPES, default='register')
    otp_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower} follows {self.following}"

class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"

class UserReport(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reporter} reported {self.reported_user}"

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    
    # Privacy & Safety
    is_activity_status_visible = models.BooleanField(default=True)
    is_location_shared = models.BooleanField(default=True)
    is_nightlife_score_visible = models.BooleanField(default=True)
    allow_tagging = models.BooleanField(default=True)
    allow_messages_from_non_followers = models.BooleanField(default=False)
    nightlife_score = models.IntegerField(default=0)
    
    # Notifications
    notify_likes = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)
    notify_new_followers = models.BooleanField(default=True)
    notify_messages = models.BooleanField(default=True)
    notify_events_rsvps = models.BooleanField(default=True)
    notify_heatmap_alerts = models.BooleanField(default=True)
    notify_promotions = models.BooleanField(default=False)
    notify_sms = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user}'s Settings"

# Signals to automatically create UserSettings when a User is created
@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_settings(sender, instance, **kwargs):
    instance.settings.save()
