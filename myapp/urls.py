# myapp/urls.py
from django.urls import path
from handlers import handler
from accounts import reg  # импортируем модуль reg (ваш views.py)
from accounts import auth_api  # создадим отдельный модуль для API endpoints

urlpatterns = [
    # Существующие пути
    path('admin_check/', handler.admin_check, name='admin_check'),
    path('check_code/', handler.check_code, name='check_code'),
    path('update_news0023399/', handler.update_news, name='update_news'),
    path('news_pop/', handler.get_news, name='get_news'),
    
    # Новые пути для аутентификации (из модуля reg)
    path('auth/google/', reg.google_login, name='google_login'),
    path('auth/google/callback/', reg.google_callback, name='google_callback'),
    path('settings/', reg.settings_page, name='settings'),
    
    # API endpoints для аутентификации (из модуля auth_api)
    path('api/validate-session/', auth_api.validate_session, name='validate_session'),
    path('api/logout/', auth_api.logout, name='logout'),
    path('auth/test-callback/', reg.test_callback, name='test_callback'),
]