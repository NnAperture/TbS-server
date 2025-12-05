# accounts/reg.py
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import requests
import json
import logging
from .client import php_client

logger = logging.getLogger(__name__)

def google_login(request):
    """Перенаправление на Google OAuth"""
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"{google_auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    logger.info(f"Redirecting to Google OAuth: {auth_url}")
    return redirect(auth_url)

def google_callback(request):
    """Обработка callback от Google"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        logger.error(f"Google OAuth error: {error}")
        return redirect(f'http://k90908k8.beget.tech/auth/login.html?error={error}')
    
    if not code:
        logger.error("No authorization code received from Google")
        return redirect('http://k90908k8.beget.tech/auth/login.html?error=no_code')
    
    try:
        # Получаем токен у Google
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.GOOGLE_REDIRECT_URI
        }
        
        logger.debug("Requesting token from Google")
        token_response = requests.post(token_url, data=token_data, timeout=30)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Получаем информацию о пользователе
        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
        
        logger.debug("Requesting user info from Google")
        user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        logger.info(f"Google user info received: {user_info.get('email', 'No email')}")
        
        # Сохраняем пользователя в БД через PHP API
        google_id = user_info['sub']
        email = user_info.get('email')
        name = user_info.get('name')
        
        logger.info(f"Creating/updating user in database: {email}")
        
        # Создаем или получаем пользователя
        user = php_client.get_or_create_user(
            google_id=google_id,
            email=email,
            name=name
        )
        logger.info(f"User created/retrieved: ID={user['id']}")
        
        # Создаем сессию
        logger.info("Creating session for user")
        session_token = php_client.create_session(user['id'])
        logger.info("Session created successfully")
        
        # Перенаправляем на фронтенд с токеном в URL
        frontend_redirect_url = f'http://k90908k8.beget.tech/auth/auth-success.html'
        
        logger.info(f"Redirecting to frontend: {frontend_redirect_url}")
        
        response = redirect(frontend_redirect_url)
        
        # Устанавливаем куку на Django домене (на случай прямого доступа к Django)
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            path='/'
        )
        
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error in google_callback: {str(e)}")
        return redirect(f'http://k90908k8.beget.tech/auth/login.html?error={str(e)}')
    except Exception as e:
        logger.error(f"Unexpected error in google_callback: {str(e)}")
        return redirect(f'http://k90908k8.beget.tech/auth/login.html?error=internal_error')

def settings_page(request):
    """Страница для передачи сессии на фронтенд"""
    logger.info("Settings page accessed")
    
    # Получаем токен из параметра URL или из куки
    session_token = request.GET.get('session_token') or request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    if not session_token:
        logger.warning("No session token found")
        return redirect('http://k90908k8.beget.tech/auth/login.html')
    
    try:
        # Валидируем сессию
        logger.debug(f"Validating session token: {session_token[:10]}...")
        session_response = php_client.validate_session(session_token)
        
        if not session_response.get('success'):
            logger.warning("Invalid session")
            response = redirect('http://k90908k8.beget.tech/auth/login.html')
            response.delete_cookie(settings.SESSION_COOKIE_NAME)
            return response
        
        user = session_response['user']
        logger.info(f"Showing settings for user: {user.get('email', user.get('google_id', 'Unknown'))}")
        
        # Создаем HTML страницу, которая сохранит токен в localStorage фронтенда
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Перенаправление на настройки</title>
            <script>
                // Сохраняем сессию в localStorage
                localStorage.setItem('session_token', '{session_token}');
                
                // Сохраняем информацию о пользователе
                const userInfo = {{
                    id: {user['id']},
                    google_id: "{user['google_id']}",
                    email: "{user.get('email', '')}",
                    name: "{user.get('name', '')}",
                    base_link: "{user.get('base_link', '')}"
                }};
                localStorage.setItem('user_info', JSON.stringify(userInfo));
                
                // Перенаправляем на страницу настроек фронтенда
                window.location.href = 'http://k90908k8.beget.tech/auth/settings.html';
            </script>
        </head>
        <body>
            <p style="text-align: center; padding: 50px; font-family: Arial;">
                Перенаправление на страницу настроек...
            </p>
        </body>
        </html>
        '''
        
        response = HttpResponse(html)
        # Также устанавливаем куку для будущих обращений к Django
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            path='/'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in settings_page: {str(e)}")
        return redirect(f'http://k90908k8.beget.tech/auth/login.html?error={str(e)}')

# ==================== Функции для отладки ====================

@csrf_exempt
def test_php_connection(request):
    """Тестовый endpoint для проверки соединения с PHP API"""
    try:
        # Тест 1: Простое подключение
        test_data = {
            'google_id': 'test123',
            'base_link': 'https://example.com/test'
        }
        
        result = php_client.get_or_create_user(**test_data)
        
        return JsonResponse({
            'success': True,
            'php_api_url': settings.PHP_API_URL + "/user_api.php",
            'php_secret_set': bool(settings.PHP_API_SECRET),
            'test_result': result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'php_api_url': settings.PHP_API_URL + "/user_api.php",
            'php_secret': settings.PHP_API_SECRET[:5] + '...' if settings.PHP_API_SECRET else 'Not set'
        }, status=500)

@csrf_exempt
def debug_check_session(request):
    """Отладочная функция для проверки сессии"""
    session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    return JsonResponse({
        'cookie_name': settings.SESSION_COOKIE_NAME,
        'cookie_present': bool(session_token),
        'cookie_value': session_token[:20] + '...' if session_token else None,
        'headers': {k: v for k, v in request.headers.items()},
        'method': request.method,
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'remote_addr': request.META.get('REMOTE_ADDR', ''),
        'get_params': dict(request.GET),
        'post_data': request.POST if request.method == 'POST' else None
    })

def test_callback(request):
    """Простой тест callback"""
    return JsonResponse({
        'code': request.GET.get('code'),
        'error': request.GET.get('error'),
        'state': request.GET.get('state'),
        'all_params': dict(request.GET)
    })