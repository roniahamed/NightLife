import uuid
from django.db import models
from django.conf import settings
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
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} at {self.venue.name}"

class EventRSVP(models.Model):
    RSVP_STATUS = (
        ('going', 'Going'),
        ('interested', 'Interested'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_rsvps')
    status = models.CharField(max_length=20, choices=RSVP_STATUS, default='going')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} is {self.status} to {self.event.title}"

class EventTicketTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_tiers')
    name = models.CharField(max_length=100) # e.g. "Early Bird", "VIP", "General Admission"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_quantity = models.PositiveIntegerField()
    sold_quantity = models.PositiveIntegerField(default=0)
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
