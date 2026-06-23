# NightLife API Summary

This document summarizes the planned API endpoints across all phases for the NightLife platform.

## Phase 5: Authentication
- `POST /api/auth/register/` - User registration.
- `POST /api/auth/verify-email/` - Verify email.
- `POST /api/auth/login/` - Login and get JWT tokens.
- `POST /api/auth/refresh/` - Refresh JWT token.
- `POST /api/auth/logout/` - Logout and invalidate token.
- `POST /api/auth/forgot-password/` - Request password reset.
- `POST /api/auth/reset-password/` - Reset password.
- `POST /api/auth/social-login/` - Firebase/Google based social login.

## Phase 6: User Module
- `GET /api/users/profile/` - Get current user profile.
- `PUT /api/users/profile/` - Update profile details.
- `POST /api/users/profile/image/` - Upload profile picture.
- `POST /api/users/{id}/follow/` - Follow a user/club.
- `POST /api/users/{id}/unfollow/` - Unfollow a user/club.
- `GET /api/users/{id}/followers/` - List followers.
- `GET /api/users/{id}/following/` - List following.
- `POST /api/users/{id}/block/` - Block user.
- `POST /api/users/{id}/report/` - Report user.

## Phase 7: Venue Module
- `GET /api/venues/` - List venues.
- `POST /api/venues/` - Create a venue (Admin/Club).
- `GET /api/venues/{id}/` - Retrieve venue details.
- `PUT /api/venues/{id}/` - Update venue.
- `DELETE /api/venues/{id}/` - Delete venue.
- `POST /api/venues/{id}/gallery/` - Upload venue gallery.
- `GET /api/venues/{id}/reviews/` - List reviews.
- `POST /api/venues/{id}/reviews/` - Create review.
- `GET /api/venues/{id}/stats/` - Venue statistics (Admin/Club).

## Phase 8: Event Module
- `GET /api/events/` - List events (with search/filter).
- `POST /api/events/` - Create an event.
- `GET /api/events/{id}/` - Retrieve event.
- `PUT /api/events/{id}/` - Update event.
- `DELETE /api/events/{id}/` - Delete event.
- `POST /api/events/{id}/gallery/` - Upload event media.
- `GET /api/events/categories/` - List categories/genres.

## Phase 9: Discovery Module
- `GET /api/discovery/search/` - Global search across venues, events, users.
- `GET /api/discovery/trending/` - Trending events/venues.
- `GET /api/discovery/heatmap/` - Heatmap data (live activity, heat score).
- `GET /api/discovery/nearby/` - Nearby venues based on coordinates.

## Phase 10: Social Module
- `GET /api/social/feed/` - User feed.
- `POST /api/social/posts/` - Create post.
- `GET /api/social/posts/{id}/` - Retrieve post.
- `PUT /api/social/posts/{id}/` - Update post.
- `DELETE /api/social/posts/{id}/` - Delete post.
- `POST /api/social/posts/{id}/like/` - Like post.
- `GET /api/social/posts/{id}/comments/` - List comments.
- `POST /api/social/posts/{id}/comments/` - Add comment.
- `POST /api/social/stories/` - Create story.
- `GET /api/social/stories/` - Feed stories.

## Phase 11: Ticketing Module
- `GET /api/tickets/types/` - List ticket types for an event.
- `POST /api/tickets/rsvp/` - RSVP to an event.
- `POST /api/tickets/checkout/` - Initiate payment/checkout.
- `GET /api/tickets/history/` - View purchased tickets.
- `GET /api/tickets/{id}/qr/` - Retrieve QR code for ticket.
- `POST /api/tickets/{id}/refund/` - Request refund.

## Phase 12 & 13: Notification & Messaging
- `GET /api/notifications/` - List notifications.
- `POST /api/notifications/read/` - Mark as read.
- `GET /api/messages/conversations/` - List chat conversations.
- `GET /api/messages/conversations/{id}/` - Retrieve messages.
- `POST /api/messages/conversations/{id}/send/` - Send message.

## Phase 15 & 16: Analytics & Admin
- `GET /api/admin/dashboard/` - Admin dashboard stats.
- `GET /api/admin/users/` - Manage users.
- `POST /api/admin/users/{id}/suspend/` - Suspend user.
- `GET /api/admin/reports/` - View reported content.
- `POST /api/admin/reports/{id}/resolve/` - Resolve report.
- `GET /api/analytics/revenue/` - Revenue stats.
- `GET /api/analytics/engagement/` - Engagement stats.
