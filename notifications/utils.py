from .models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_notification_to_user(recipient, message: str):
    """
    Internal utility to create and send a notification to a user.
    """
    # Save in DB
    notification = Notification.objects.create(
        recipient=recipient,
        message=message
    )

    # WebSocket send
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{recipient.id}",
        {
            "type": "send_notification",
            "message": message,
        }
    )

    return notification


async def send_real_time_notification_to_user(recipient, message: str):
    """
    Send a real-time notification to a user (no DB save).
    This will send the message to the user's WebSocket group.
    """
    # Get the channel layer
    channel_layer = get_channel_layer()

    # Send the notification to the WebSocket group of the recipient
    await channel_layer.group_send(
        f"user_{recipient.id}",  # WebSocket group for the user
        {
            "type": "send_notification",  # This will be handled by the consumer
            "message": message,  # The message content
        }
    )

