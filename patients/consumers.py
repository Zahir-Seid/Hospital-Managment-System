import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from users.auth import AsyncAuthBearer
from notifications.utils import send_real_time_notification_to_user

auth = AsyncAuthBearer()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Authenticate user using AsyncAuthBearer when WebSocket connects.
        """
        from users.models import User 
        from django.utils.timezone import now 

        try:
            query_string = self.scope["query_string"].decode()
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]

            if not token:
                await self.close(code=4000)  # Missing token
                return

            from users.models import User
            from ninja_jwt.tokens import AccessToken  # This works with django-ninja-jwt

            try:
                validated_token = AccessToken(token)
                user_id = validated_token["user_id"]
                self.user = await User.objects.filter(id=user_id).afirst()
            except Exception as e:
                print(f"Token error: {e}")
                await self.close(code=4001)  # Invalid token
                return

            if not self.user:
                await self.close(code=4001)  # Invalid token
                return

            # Store the authenticated user in the WebSocket scope
            self.scope["user"] = self.user

            # Ensure a recipient_id is passed in query parameters
            receiver_id = query_params.get("receiver_id", [None])[0]
            if not receiver_id:
                await self.close(code=4003)  # Missing recipient ID
                return

            self.receiver = await User.objects.filter(id=receiver_id).afirst()

            if not self.receiver:
                await self.close(code=4004)  # Recipient not found
                return

            # Store the receiver in the WebSocket scope
            self.scope["receiver"] = self.receiver

            # Unique chat room for doctor-patient communication
            self.room_group_name = f"chat_{min(self.user.id, self.receiver.id)}_{max(self.user.id, self.receiver.id)}"

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

        except Exception as e:
            print(f"Error during WebSocket connection: {e}")
            await self.close(code=4002)  # Unexpected error

    async def disconnect(self, close_code):
        """
        Remove user from WebSocket channel on disconnect.
        """
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        from .models import ChatMessage  
        from django.utils.timezone import now

        try:
            data = json.loads(text_data)
            message_text = data.get("message")

            if not message_text:
                await self.send(text_data=json.dumps({"error": "Message is required"}))
                return

            receiver = self.receiver  # Use stored receiver from `connect()`

            # Save message
            chat_message = await ChatMessage.objects.acreate(
                sender=self.user,
                receiver=receiver,
                message=message_text,
                timestamp=now(),
            )
            
            await send_real_time_notification_to_user(receiver, f"Chat from {self.user.username} ")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "sender": self.user.username,
                    "sender_id": self.user.id,  
                    "receiver": receiver.username,
                    "receiver_id": receiver.id,
                    "message": message_text,
                    "timestamp": str(chat_message.timestamp),
                },
            )

        except Exception as e:
            print(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({"error": "Internal server error"}))


    async def chat_message(self, event):
        """
        Send received message to WebSocket clients.
        """
        await self.send(text_data=json.dumps(event))
