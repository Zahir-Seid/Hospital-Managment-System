import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from notifications.routing import websocket_urlpatterns as notifications_ws
from patients.routing import websocket_urlpatterns as chat_ws  
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HospitalManagmentSystem.settings")
django.setup()

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(  
            URLRouter(
                notifications_ws + chat_ws 
            )
        ),
    }
)
