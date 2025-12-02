# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion
from accounts import reg

import threading

urlpatterns = [
    path('admin_check/', handler.admin_check),
    path('check_code/', handler.check_code),
    path('update_news0023399/', handler.update_news),
    path('news_pop/', handler.get_news),

    path("start_create_account_api", reg.start_create_account_api),
    path("get_user_data_api", reg.get_user_data_api),
    path("telegram_send_code_api", reg.telegram_send_code_api),
    path("telegram_verify_code_api", reg.telegram_verify_code_api),
    path("complete_account_creation_api", reg.complete_account_creation_api),
]
