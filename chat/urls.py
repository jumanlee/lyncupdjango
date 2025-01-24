from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [

    # path('<str:groupname>/', views.room, name='room'),

    # #this is only for pytest purposes, as the websocket opening is dynamically handled from Queue.
    # re_path(r"ws/queue/$", GroupConsumer.as_asgi()),
]