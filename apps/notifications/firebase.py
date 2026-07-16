import os
import logging
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging
from .models import Notification, FCMDevice

logger = logging.getLogger(__name__)

# Try to initialize Firebase Admin SDK
try:
    if not firebase_admin._apps:
        # You can point this to a JSON file path using an environment variable
        # For example, FIREBASE_CREDENTIALS=/path/to/serviceAccountKey.json
        cred_path = os.environ.get('FIREBASE_CREDENTIALS')
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized successfully.")
        else:
            logger.warning("FIREBASE_CREDENTIALS not set or file not found. Push notifications will not be sent.")
except Exception as e:
    logger.error(f"Error initializing Firebase Admin: {e}")


def send_user_notification(user, title, message, notification_type='general', related_object_id=None, data=None):
    """
    Creates a Notification in DB and sends a push notification via Firebase FCM.
    """
    # 1. Save to Database
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        related_object_id=related_object_id
    )

    # 2. Check if firebase is initialized
    if not firebase_admin._apps:
        logger.warning("Firebase not initialized. Notification saved to DB only.")
        return notification

    # 3. Get user's active devices
    devices = FCMDevice.objects.filter(user=user, is_active=True)
    tokens = list(devices.values_list('registration_id', flat=True))
    
    if not tokens:
        logger.info(f"No active FCM devices for user {user.email}")
        return notification

    # 4. Prepare message
    # FCM data payload must contain only string keys and string values
    payload_data = {}
    if data:
        for k, v in data.items():
            payload_data[str(k)] = str(v)
            
    payload_data['notification_type'] = str(notification_type)
    if related_object_id:
        payload_data['related_object_id'] = str(related_object_id)
    payload_data['notification_id'] = str(notification.id)

    message_obj = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=message,
        ),
        data=payload_data,
        tokens=tokens,
    )

    # 5. Send message
    try:
        response = messaging.send_each_for_multicast(message_obj)
        logger.info(f"Successfully sent {response.success_count} messages; {response.failure_count} failures.")
        
        # 6. Handle edge cases (invalid tokens)
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # These errors indicate the token is invalid or unregistered
                    if isinstance(resp.exception, (
                        messaging.UnregisteredError, 
                        messaging.SenderIdMismatchError, 
                        messaging.InvalidArgumentError
                    )):
                        failed_tokens.append(tokens[idx])
            
            if failed_tokens:
                logger.info(f"Deactivating {len(failed_tokens)} invalid tokens.")
                FCMDevice.objects.filter(registration_id__in=failed_tokens).update(is_active=False)
                
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")

    return notification
