# myapp/urls.py
from django.urls import path
from handlers import handler

urlpatterns = [
    path('account/', handler.account, name='hello_world'),
]
