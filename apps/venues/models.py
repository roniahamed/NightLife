import uuid
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Amenity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='amenities/icons/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Amenities'
        ordering = ['name']

    def __str__(self):
        return self.name

class VenueCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Venue Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class Venue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venue_profile')
    name = models.CharField(max_length=255)
    description = models.TextField()
    address = models.CharField(max_length=255)
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Missing UI Fields
    is_approved = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='venues/profiles/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='venues/covers/', null=True, blank=True)
    
    PRICE_TIERS = (
        (1, '$'),
        (2, '$$'),
        (3, '$$$'),
        (4, '$$$$'),
    )
    price_tier = models.IntegerField(choices=PRICE_TIERS, null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    categories = models.ManyToManyField(VenueCategory, related_name='venues', blank=True)

    amenities = models.ManyToManyField(Amenity, related_name='venues', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class VenueGallery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='venues/gallery/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name_plural = 'Venue Galleries'

    def __str__(self):
        return f"{self.venue.name} - Image {self.order}"

class VenueOperatingHour(models.Model):
    DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='operating_hours')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('venue', 'day_of_week')
        ordering = ['day_of_week']

    def __str__(self):
        return f"{self.venue.name} - {self.get_day_of_week_display()}"

class VenueReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='venue_reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('venue', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user} for {self.venue.name}"

class VenueStatistic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.OneToOneField(Venue, on_delete=models.CASCADE, related_name='statistic')
    total_views = models.PositiveIntegerField(default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    favorites_count = models.PositiveIntegerField(default=0)
    followers_count = models.PositiveIntegerField(default=0)
    heat_score = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.venue.name}"

class VenueFollow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='venue_follows')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'venue')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} follows {self.venue.name}"
