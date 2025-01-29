from ninja import Router
from django.shortcuts import get_object_or_404
from users.models import User
from .models import Notification
from .schemas import NotificationCreate, NotificationOut
from users.views import AuthBearer  

notifications_router = Router(tags=["Notifications"], auth=AuthBearer())

# Send a notification
@notifications_router.post("/send", response={200: NotificationOut, 400: dict})
def send_notification(request, payload: NotificationCreate):
    """
    Create a notification for a user.
    """
    sender = request.auth  # Authenticated user
    recipient = get_object_or_404(User, id=payload.recipient_id)

    notification = Notification.objects.create(
        recipient=recipient,
        message=payload.message
    )
    return notification


# List notifications for the logged-in user
@notifications_router.get("/list", response={200: list[NotificationOut]})
def list_notifications(request):
    """
    Retrieve notifications for the logged-in user.
    """
    user = request.auth
    return Notification.objects.filter(recipient=user)


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
    return notification


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
