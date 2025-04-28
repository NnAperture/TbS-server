# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion

urlpatterns = [
    path('acc/', handler.account, name='account'),
    path('seccion/', seccion.seccion, name='seccion'),
]
