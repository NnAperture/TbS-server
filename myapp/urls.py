# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion
from accounts.reg import register_api, login_api, me_api, logout_api

import threading

urlpatterns = [
    path('admin_check/', handler.admin_check),
    path('check_code/', handler.check_code),
    path('update_news0023399/', handler.update_news),
    path('news_pop/', handler.get_news),

    path("api/register/", register_api),
    path("api/login/", login_api),
    path("api/me/", me_api),
    path("api/logout/", logout_api),
]