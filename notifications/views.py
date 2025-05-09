from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Notification
from .schemas import NotificationCreate, NotificationOut
from users.auth import AuthBearer  
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

notifications_router = Router(tags=["Notifications"], auth=AuthBearer())

# Send a notification 
@notifications_router.post("/send", response={200: NotificationOut, 400: dict})
def send_notification(request, payload: NotificationCreate):
    """
    Create a notification for a user and send it in real-time via WebSockets.
    """
    recipient = get_object_or_404(User, id=payload.recipient_id)

    # Store notification in the database
    notification = Notification.objects.create(
        recipient=recipient,
        message=payload.message
    )

    # Get WebSocket channel layer
    channel_layer = get_channel_layer()

    # Send real-time WebSocket notification
    async_to_sync(channel_layer.group_send)(
        f"user_{recipient.id}",
        {
            "type": "send_notification",
            "message": payload.message,
        }
    )

    return notification

@notifications_router.get("/list", response={200: list[NotificationOut]})
def list_notifications(request):
    """
    Retrieve notifications for the logged-in user.
    """
    user = request.auth

    notifications = Notification.objects.filter(recipient=user)

    return [
        NotificationOut(
            id=n.id,
            recipient=n.recipient.username,
            message=n.message,
            status=n.status,
            created_at=n.created_at,
        )
        for n in notifications
    ]



# Mark a notification as read
@notifications_router.put("/mark-read/{notification_id}", response={200: NotificationOut, 400: dict})
def mark_notification_read(request, notification_id: int):
    """
    Mark a notification as read.
    """
    user = request.auth
    notification = get_object_or_404(Notification, id=notification_id, recipient=user)

    notification.status = "read"
    notification.save()

    # Manually convert to dict with string fields
    return {
        "id": notification.id,
        "recipient": str(notification.recipient),  # convert User to string
        "message": notification.message,
        "status": notification.status,
        "created_at": notification.created_at,
    }



# Delete a notification
@notifications_router.delete("/delete/{notification_id}", response={200: dict, 400: dict})
def delete_notification(request, notification_id: int):
    """
    Delete a notification.
    """
    user = request.auth
    notification = get_object_or_404(Notification, id=notification_id, recipient=user)

    notification.delete()
    return {"message": "Notification deleted successfully"}