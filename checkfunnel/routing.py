from django.urls import re_path
from chat import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<client_id>[\w-]+)/(?P<session_id>[\w-]+)/$', consumers.ChatConsumer.as_asgi()),
]
