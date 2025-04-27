# myapp/urls.py
from django.urls import path
from handlers import handler

urlpatterns = [
    path('acc/', handler.account, name='account'),
]
