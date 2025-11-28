# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion

import threading

urlpatterns = [
    path('admin_check/', handler.admin_check),
    path('check_code/', handler.check_code),
    path('update_news0023399/', handler.update_news),
    path('news_pop/', handler.get_news),
]
