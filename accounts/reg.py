from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import requests
import json
from .client import php_client


@csrf_exempt
def google_login(request):
    """Перенаправление на Google OAuth"""
    # URL для авторизации Google
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
    
    return redirect(auth_url)

@csrf_exempt
def google_callback(request):
    """Обработка callback от Google"""
    code = request.GET.get('code')
    
    if not code:
        return JsonResponse({'error': 'No code provided'}, status=400)
    
    # Получаем токен у Google
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.GOOGLE_REDIRECT_URI
    }
    
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    
    if 'access_token' not in token_json:
        return JsonResponse({'error': 'Failed to get access token'}, status=400)
    
    # Получаем информацию о пользователе
    user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
    user_info_response = requests.get(user_info_url, headers=headers)
    user_info = user_info_response.json()
    
    # Сохраняем пользователя в БД через PHP API
    google_id = user_info['sub']
    base_link = f"https://api.example.com/users/{google_id}"  # Замените на реальный base_link
    email = user_info.get('email')
    name = user_info.get('name')
    
    # Создаем или получаем пользователя
    user_response = php_client.get_or_create_user(
        google_id=google_id,
        base_link=base_link,
        email=email,
        name=name
    )
    
    if not user_response.get('success'):
        return JsonResponse({'error': 'Failed to create user'}, status=500)
    
    user = user_response['user']
    
    # Создаем сессию
    session_response = php_client.create_session(user['id'])
    
    if not session_response.get('success'):
        return JsonResponse({'error': 'Failed to create session'}, status=500)
    
    session_token = session_response['session_token']
    
    # Перенаправляем на фронтенд с токеном сессии
    frontend_url = f"http://your-frontend-server.com/auth/success?session={session_token}"
    
    response = redirect(frontend_url)
    # Устанавливаем куку для сессии
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_COOKIE_AGE,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        samesite=settings.SESSION_COOKIE_SAMESITE
    )
    
    return response

@csrf_exempt
@require_http_methods(["POST"])
def validate_session(request):
    """Валидация сессии (для AJAX запросов с фронтенда)"""
    session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    if not session_token:
        return JsonResponse({'authenticated': False}, status=401)
    
    try:
        session_response = php_client.validate_session(session_token)
        
        if session_response.get('success'):
            user = session_response['user']
            return JsonResponse({
                'authenticated': True,
                'user': {
                    'id': user['id'],
                    'google_id': user['google_id'],
                    'email': user.get('email'),
                    'name': user.get('name'),
                    'base_link': user.get('base_link')
                }
            })
        else:
            return JsonResponse({'authenticated': False}, status=401)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    """Выход из системы"""
    session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    if session_token:
        try:
            php_client.delete_session(session_token)
        except:
            pass
    
    response = JsonResponse({'success': True})
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response

@csrf_exempt
def settings_page(request):
    """Страница настроек"""
    session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    if not session_token:
        # Если нет сессии, перенаправляем на страницу входа
        return redirect('http://your-frontend-server.com/login')
    
    # Валидируем сессию
    try:
        session_response = php_client.validate_session(session_token)
        
        if not session_response.get('success'):
            response = redirect('http://your-frontend-server.com/login')
            response.delete_cookie(settings.SESSION_COOKIE_NAME)
            return response
        
        user = session_response['user']
        
        # Генерируем HTML страницу настроек
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Настройки аккаунта</title>
            <script>
                // Сохраняем информацию о пользователе в localStorage
                const userInfo = {{
                    id: {user['id']},
                    google_id: "{user['google_id']}",
                    email: "{user.get('email', '')}",
                    name: "{user.get('name', '')}",
                    base_link: "{user.get('base_link', '')}"
                }};
                localStorage.setItem('user_info', JSON.stringify(userInfo));
                
                // Перенаправляем на фронтенд
                window.location.href = "http://your-frontend-server.com/settings";
            </script>
        </head>
        <body>
            <p>Перенаправление на страницу настроек...</p>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content)
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

