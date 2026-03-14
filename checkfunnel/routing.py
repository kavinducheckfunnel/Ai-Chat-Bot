from django.urls import re_path
from chat import consumers
from users.consumers import AdminDashboardConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<client_id>[\w-]+)/(?P<session_id>[\w-]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/admin/dashboard/$', AdminDashboardConsumer.as_asgi()),
]
