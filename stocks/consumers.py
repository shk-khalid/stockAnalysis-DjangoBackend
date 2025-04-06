import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

# Configure a logger for this module
logger = logging.getLogger(__name__)

class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Check if user is authenticated
        if self.scope["user"].is_anonymous:
            logger.warning("Connection attempt by an unauthenticated user; closing connection with code 403.")
            await self.close(code=403)  # Reject connection if unauthenticated
        else:
            self.group_name = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            logger.info(f"User {self.scope['user'].id} connected. Added to group {self.group_name}.")
            await self.accept()

    async def disconnect(self, close_code):
        # Log disconnection details with context
        user_info = self.scope["user"].id if not self.scope["user"].is_anonymous else "Anonymous"
        logger.info(f"User {user_info} disconnecting with close code {close_code}. "
                    f"Channel: {self.channel_name}, Group: {getattr(self, 'group_name', 'N/A')}.")
        
        # Optionally, add more details if needed (e.g., request headers, scope info, etc.)
        if hasattr(self, "group_name") and self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_alert(self, event):
        alert = event["alert"]
        await self.send(text_data=json.dumps(alert))  # Send alert JSON to client
