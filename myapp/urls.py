# myapp/urls.py
from django.urls import path
from handlers import handler
from accounts.reg import (
    google_login, google_callback, dashboard, 
    api_user_info, logout, api_get_pub_data, api_update_profile
)

urlpatterns = [
    path('admin_check/', handler.admin_check, name='admin_check'),
    path('check_code/', handler.check_code, name='check_code'),
    path('update_news0023399/', handler.update_news, name='update_news'),
    path('news_pop/', handler.get_news, name='get_news'),
    
    path('oauth/google/', google_login, name='google_login'),
    path('oauth/google/callback/', google_callback, name='google_callback'),
    path('dashboard/', dashboard, name='dashboard'),
    path('api/user-info/', api_user_info, name='api_user_info'),
    path('api/pub-data/<int:pub_id>/', api_get_pub_data, name='api_get_pub_data'),
    path('api/update-profile/', api_update_profile, name='api_update_profile'),
    path('logout/', logout, name='logout'),
    path('', dashboard),
]