import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockAnalysis_server.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from stocks.urls import websocket_urlpatterns
from stocks.middleware import JWTAuthMiddleware
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
