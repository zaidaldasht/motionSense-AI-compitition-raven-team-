from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/read/", consumers.ReadConsumer.as_asgi()),
]
