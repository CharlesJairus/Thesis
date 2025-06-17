from django.urls import path
from .consumer import NotifConsumer

wspattern =[
    path("ws/notification",NotifConsumer.as_asgi())
]