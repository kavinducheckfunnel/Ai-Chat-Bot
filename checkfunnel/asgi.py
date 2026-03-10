import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import checkfunnel.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'checkfunnel.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            checkfunnel.routing.websocket_urlpatterns
        )
    ),
})
