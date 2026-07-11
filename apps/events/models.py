import uuid
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from apps.venues.models import Venue

User = settings.AUTH_USER_MODEL

class EventCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Event Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    cover_image = models.ImageField(upload_to='events/covers/', null=True, blank=True)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ticket_url = models.URLField(blank=True, null=True)
    
    AGE_RESTRICTIONS = (
        ('none', 'No Restriction'),
        ('18+', '18+'),
        ('21+', '21+'),
    )
    age_restriction = models.CharField(max_length=10, choices=AGE_RESTRICTIONS, default='none')
    categories = models.ManyToManyField(EventCategory, related_name='events', blank=True)
    
    capacity = models.PositiveIntegerField(null=True, blank=True)
    custom_venue_address = models.CharField(max_length=255, null=True, blank=True)
    
    DRESS_CODES = (
        ('Upscale Nightclub', 'Upscale Nightclub'),
        ('Casual', 'Casual'),
        ('Smart Casual', 'Smart Casual'),
        ('Rave / Creative', 'Rave / Creative'),
        ('Pool Attire', 'Pool Attire'),
        ('Black Tie', 'Black Tie'),
        ('No Dress Code', 'No Dress Code'),
    )
    dress_code = models.CharField(max_length=50, choices=DRESS_CODES, default='No Dress Code')
    
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} at {self.venue.name}"

class EventLineup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='lineup')
    artist_name = models.CharField(max_length=255)
    artist_image = models.ImageField(upload_to='events/lineup/', null=True, blank=True)
    
    ROLE_CHOICES = (
        ('headliner', 'Headliner'),
        ('co_headliner', 'Co-Headliner'),
        ('support', 'Support'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='support')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.artist_name} ({self.get_role_display()}) at {self.event.title}"

class EventRSVP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_rsvps')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} is going to {self.event.title}"

class EventTicketTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_tiers')
    name = models.CharField(max_length=100) # e.g. "Early Bird", "VIP", "General Admission"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_quantity = models.PositiveIntegerField()
    sold_quantity = models.PositiveIntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.event.title}"

class TicketPurchase(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_purchases')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_purchases')
    ticket_tier = models.ForeignKey(EventTicketTier, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    funds_transferred_to_venue = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Purchase {self.id} by {self.user}"

class StripeWebhookEvent(models.Model):
    stripe_event_id = models.CharField(max_length=255, primary_key=True)
    type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} - {self.stripe_event_id}"
