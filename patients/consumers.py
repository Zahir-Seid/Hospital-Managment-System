import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from users.models import User
from .models import ChatMessage
from django.utils.timezone import now
from users.auth import AsyncAuthBearer

auth = AsyncAuthBearer()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Authenticate user using AsyncAuthBearer when WebSocket connects.
        """
        try:
            query_string = self.scope["query_string"].decode()
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]

            if not token:
                await self.close(code=4000)  # Missing token
                return

            self.user = await auth.authenticate(self.scope, token)

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
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        """
        try:
            data = json.loads(text_data)
            receiver_id = data.get("receiver_id")
            message_text = data.get("message")

            if not receiver_id or not message_text:
                await self.send(text_data=json.dumps({"error": "Invalid message format"}))
                return

            receiver = await User.objects.filter(id=receiver_id).afirst()

            if not receiver:
                await self.send(text_data=json.dumps({"error": "Receiver not found"}))
                return

            # Ensure that the sender is either the patient or doctor in the chat
            if self.user not in [self.receiver, receiver]:
                await self.send(text_data=json.dumps({"error": "Unauthorized access"}))
                return

            # Use a unique room name for doctor-patient chat
            self.room_group_name = f"chat_{min(self.user.id, receiver.id)}_{max(self.user.id, receiver.id)}"

            # Save message in the database
            chat_message = await ChatMessage.objects.acreate(
                sender=self.user,
                receiver=receiver,
                message=message_text,
                timestamp=now(),
            )

            # Send message only to the recipient in the same room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "sender": self.user.username,
                    "receiver": receiver.username,
                    "message": message_text,
                    "timestamp": str(chat_message.timestamp),
                },
            )

        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
            await self.send(text_data=json.dumps({"error": "Internal server error"}))

    async def chat_message(self, event):
        """
        Send received message to WebSocket clients.
        """
        await self.send(text_data=json.dumps(event))
