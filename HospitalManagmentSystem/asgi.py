import os
import django

# Set environment variable BEFORE anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HospitalManagmentSystem.settings")

# Setup Django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import AFTER setup
from notifications.routing import websocket_urlpatterns as notifications_ws
from patients.routing import websocket_urlpatterns as chat_ws

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(notifications_ws + chat_ws)
    ),
})

#uvicorn HospitalManagmentSystem.asgi:application --reload
