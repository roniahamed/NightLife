from django.db import transaction
from django.db.models import Avg
from django.contrib.gis.geos import Point
from .models import Venue, VenueGallery, VenueOperatingHour, VenueReview, VenueStatistic, VenueFollow

@transaction.atomic
def create_venue(owner, **data):
    """
    Creates a new Venue and its associated VenueStatistic.
    Handles assigning amenities and converting lat/lon to Point.
    """
    amenities = data.pop('amenities', [])
    categories = data.pop('categories', [])
    
    lat = data.pop('latitude', None)
    lng = data.pop('longitude', None)
    if lat is not None and lng is not None:
        data['location'] = Point(lng, lat, srid=4326)
        
    venue = Venue.objects.create(owner=owner, **data)
    
    if amenities:
        venue.amenities.set(amenities)
        
    if categories:
        venue.categories.set(categories)
        
    # Initialize statistics for the new venue
    VenueStatistic.objects.create(venue=venue)
    
    return venue

@transaction.atomic
def update_venue(venue, **data):
    """
    Updates an existing Venue. Handles assigning amenities and location.
    """
    amenities = data.pop('amenities', None)
    categories = data.pop('categories', None)
    
    lat = data.pop('latitude', None)
    lng = data.pop('longitude', None)
    if lat is not None and lng is not None:
        venue.location = Point(lng, lat, srid=4326)
    
    for field, value in data.items():
        setattr(venue, field, value)
    venue.save()
    
    if amenities is not None:
        venue.amenities.set(amenities)
        
    if categories is not None:
        venue.categories.set(categories)
        
    return venue

def add_venue_gallery_image(venue, image, caption="", order=0):
    """
    Adds an image to a venue's gallery.
    """
    return VenueGallery.objects.create(
        venue=venue,
        image=image,
        caption=caption,
        order=order
    )

@transaction.atomic
def set_operating_hours(venue, hours_data):
    """
    Sets or updates operating hours for a venue.
    hours_data is a list of dicts: [{'day_of_week': 0, 'open_time': '09:00', 'close_time': '17:00', 'is_closed': False}, ...]
    """
    # Simple strategy: clear existing and recreate to handle all updates easily
    venue.operating_hours.all().delete()
    
    hours_objects = []
    for hd in hours_data:
        hours_objects.append(VenueOperatingHour(venue=venue, **hd))
        
    if hours_objects:
        VenueOperatingHour.objects.bulk_create(hours_objects)

@transaction.atomic
def add_venue_review(venue, user, rating, comment=""):
    """
    Adds or updates a review for a venue by a user,
    and updates the venue statistics accordingly.
    """
    review, created = VenueReview.objects.update_or_create(
        venue=venue,
        user=user,
        defaults={
            'rating': rating,
            'comment': comment
        }
    )
    
    _update_venue_rating_stats(venue)
    return review

def _update_venue_rating_stats(venue):
    """
    Helper function to recalculate and update the venue's average rating and total reviews.
    """
    stats, _ = VenueStatistic.objects.get_or_create(venue=venue)
    aggregate = venue.reviews.aggregate(
        avg_rating=Avg('rating'),
    )
    
    stats.average_rating = aggregate['avg_rating'] or 0.00
    stats.total_reviews = venue.reviews.count()
    stats.followers_count = venue.followers.count()
    stats.save()

def get_dashboard_stats(venue):
    from apps.events.models import TicketPurchase, Event
    from django.db.models import Sum
    from apps.events.serializers import TicketPurchaseSerializer
    import stripe
    
    purchases = TicketPurchase.objects.filter(event__venue=venue, status='completed')
    
    total_tickets_sold = purchases.aggregate(total=Sum('quantity'))['total'] or 0
    total_revenue = purchases.aggregate(total=Sum('total_amount'))['total'] or 0
    platform_fees = purchases.aggregate(total=Sum('platform_fee'))['total'] or 0
    net_earnings = total_revenue - platform_fees
    
    active_events_count = Event.objects.filter(venue=venue, is_active=True).count()
    recent_transactions = purchases.order_by('-created_at')[:5]
    
    stripe_available_balance = 0.0
    stripe_pending_balance = 0.0
    
    if venue.stripe_account_id and venue.stripe_account_status == 'active':
        try:
            balance = stripe.Balance.retrieve(stripe_account=venue.stripe_account_id)
            stripe_available_balance = sum(b.amount for b in balance.available) / 100.0
            stripe_pending_balance = sum(b.amount for b in balance.pending) / 100.0
        except stripe.error.StripeError:
            pass
            
    return {
        "total_tickets_sold": total_tickets_sold,
        "total_revenue": float(total_revenue),
        "platform_fees_paid": float(platform_fees),
        "net_earnings": float(net_earnings),
        "stripe_available_balance": stripe_available_balance,
        "stripe_pending_balance": stripe_pending_balance,
        "active_events_count": active_events_count,
        "recent_transactions": TicketPurchaseSerializer(recent_transactions, many=True).data
    }

def create_stripe_onboarding(venue, refresh_url, return_url):
    import stripe
    
    # Create Stripe Account if not exists or if previously disconnected
    if not venue.stripe_account_id or venue.stripe_account_status == 'disconnected':
        account = stripe.Account.create(
            type="express",
            email=venue.owner.email,
            business_type="company",
            company={"name": venue.name},
        )
        venue.stripe_account_id = account.id
        venue.stripe_account_status = 'pending'
        venue.save()
    
    # Create Account Link
    account_link = stripe.AccountLink.create(
        account=venue.stripe_account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    
    return account_link.url

def generate_stripe_dashboard_link(venue):
    """
    Generates a Stripe Express dashboard login link for the venue owner.
    """
    import stripe
    from django.conf import settings
    
    if not venue.stripe_account_id or venue.stripe_account_status != 'active':
        raise ValueError("Venue must have an active Stripe account to view the dashboard.")
        
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        login_link = stripe.Account.create_login_link(venue.stripe_account_id)
        return login_link.url
    except stripe.error.StripeError as e:
        raise ValueError(str(e))

def increment_venue_view(venue):
    """
    Increments the view count for a venue.
    """
    stats, _ = VenueStatistic.objects.get_or_create(venue=venue)
    stats.total_views += 1
    stats.save()

@transaction.atomic
def follow_venue(user, venue):
    """
    Follows a venue and increments the follower count.
    """
    follow, created = VenueFollow.objects.get_or_create(user=user, venue=venue)
    if created:
        stats, _ = VenueStatistic.objects.get_or_create(venue=venue)
        stats.followers_count = venue.followers.count()
        stats.save()
    return follow

@transaction.atomic
def unfollow_venue(user, venue):
    """
    Unfollows a venue and decrements the follower count.
    """
    deleted, _ = VenueFollow.objects.filter(user=user, venue=venue).delete()
    if deleted:
        stats, _ = VenueStatistic.objects.get_or_create(venue=venue)
        stats.followers_count = venue.followers.count()
        stats.save()

