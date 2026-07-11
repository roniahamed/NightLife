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
    from django.utils import timezone
    from datetime import timedelta
    import stripe
    
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    # 1. Revenue This Week & Change
    purchases_this_week = TicketPurchase.objects.filter(event__venue=venue, status='completed', created_at__gte=one_week_ago)
    purchases_last_week = TicketPurchase.objects.filter(event__venue=venue, status='completed', created_at__gte=two_weeks_ago, created_at__lt=one_week_ago)
    
    agg_this_week = purchases_this_week.aggregate(gross=Sum('total_amount'), fees=Sum('platform_fee'))
    revenue_this_week = (agg_this_week['gross'] or 0) - (agg_this_week['fees'] or 0)
    
    agg_last_week = purchases_last_week.aggregate(gross=Sum('total_amount'), fees=Sum('platform_fee'))
    revenue_last_week = (agg_last_week['gross'] or 0) - (agg_last_week['fees'] or 0)
    
    if revenue_last_week > 0:
        revenue_change = float(((revenue_this_week - revenue_last_week) / revenue_last_week) * 100)
    else:
        revenue_change = 100.0 if revenue_this_week > 0 else 0.0
        
    # 2. Total Followers & Change
    total_followers = venue.statistic.followers_count if hasattr(venue, 'statistic') else venue.followers.count()
    followers_this_week = VenueFollow.objects.filter(venue=venue, created_at__gte=one_week_ago).count()
    
    new_followers_this_week = followers_this_week
    
    # 3. Tickets Sold & Change
    tickets_this_week = purchases_this_week.aggregate(total=Sum('quantity'))['total'] or 0
    tickets_last_week = purchases_last_week.aggregate(total=Sum('quantity'))['total'] or 0
    
    if tickets_last_week > 0:
        tickets_change = float(((tickets_this_week - tickets_last_week) / tickets_last_week) * 100)
    else:
        tickets_change = 100.0 if tickets_this_week > 0 else 0.0
        
    # 4. Heat Score
    heat_score = venue.statistic.heat_score if hasattr(venue, 'statistic') else 0
    
    # 5. Revenue Chart Data (Last 7 days)
    chart_data = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        agg = TicketPurchase.objects.filter(
            event__venue=venue, 
            status='completed', 
            created_at__gte=day_start, 
            created_at__lt=day_end
        ).aggregate(gross=Sum('total_amount'), fees=Sum('platform_fee'))
        
        gross = agg['gross'] or 0
        fees = agg['fees'] or 0
        day_revenue = gross - fees
        
        chart_data.append({
            'day': day_start.strftime('%a'),
            'revenue': float(day_revenue)
        })
        
    # 6. Recent Activity
    recent_activities = []
    
    recent_followers = VenueFollow.objects.filter(venue=venue, created_at__gte=one_week_ago).order_by('-created_at')[:5]
    for f in recent_followers:
        recent_activities.append({
            'type': 'follower',
            'message': f'New follower milestone: {total_followers} followers!' if total_followers > 0 and total_followers % 100 == 0 else f'New follower: {f.user.username}',
            'time': f.created_at,
            'icon': 'user'
        })
        
    recent_purchases = purchases_this_week.order_by('-created_at')[:5]
    for p in recent_purchases:
        recent_activities.append({
            'type': 'ticket',
            'message': f'{p.quantity} new tickets sold for {p.event.title} event',
            'time': p.created_at,
            'icon': 'ticket'
        })
        
    recent_reviews = VenueReview.objects.filter(venue=venue, created_at__gte=one_week_ago).order_by('-created_at')[:5]
    for r in recent_reviews:
        recent_activities.append({
            'type': 'review',
            'message': f'New {r.rating}-star review from {r.user.username}',
            'time': r.created_at,
            'icon': 'star'
        })
        
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:10]
    
    # Original Data for backward compatibility
    all_purchases = TicketPurchase.objects.filter(event__venue=venue, status='completed')
    total_tickets_sold = all_purchases.aggregate(total=Sum('quantity'))['total'] or 0
    total_revenue_all = all_purchases.aggregate(total=Sum('total_amount'))['total'] or 0
    platform_fees = all_purchases.aggregate(total=Sum('platform_fee'))['total'] or 0
    net_earnings = total_revenue_all - platform_fees
    
    active_events_count = Event.objects.filter(venue=venue, is_active=True).count()
    recent_transactions = all_purchases.order_by('-created_at')[:5]
    
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
        # Dashboard UI requirements
        "revenue_this_week": float(revenue_this_week),
        "revenue_percentage_change": round(revenue_change, 1),
        "total_followers": total_followers,
        "new_followers_this_week": new_followers_this_week,
        "tickets_sold_this_week": tickets_this_week,
        "tickets_sold_percentage_change": round(tickets_change, 1),
        "heat_score": heat_score,
        "revenue_chart_data": chart_data,
        "recent_activity": [{
            'type': activity['type'],
            'message': activity['message'],
            'time': activity['time'].isoformat(),
            'icon': activity['icon']
        } for activity in recent_activities],
        
        # Original fields
        "total_tickets_sold": total_tickets_sold,
        "total_revenue": float(total_revenue_all),
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

