# accounts/auth_api.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from django.conf import settings
from .client import php_client

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def validate_session(request):
    """Валидация сессии с улучшенной отладкой"""
    
    # Обработка CORS preflight запросов
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "http://k90908k8.beget.tech"
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
    
    try:
        # Логируем все куки для отладки
        logger.info(f"Request cookies: {dict(request.COOKIES)}")
        logger.info(f"Session cookie name: {settings.SESSION_COOKIE_NAME}")
        
        # Получаем токен из кук
        session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        
        if not session_token:
            logger.warning(f"No session token found in cookies. Available cookies: {list(request.COOKIES.keys())}")
            response = JsonResponse({
                'authenticated': False, 
                'error': 'No session token',
                'debug': {
                    'cookie_name': settings.SESSION_COOKIE_NAME,
                    'available_cookies': list(request.COOKIES.keys())
                }
            }, status=200)  # Используем 200 вместо 401 для фронтенда
            
            # Добавляем CORS заголовки
            response["Access-Control-Allow-Origin"] = "http://k90908k8.beget.tech"
            response["Access-Control-Allow-Credentials"] = "true"
            return response
        
        logger.debug(f"Validating session token: {session_token[:20]}...")
        
        # Валидируем сессию через PHP API
        session_response = php_client.validate_session(session_token)
        
        if session_response.get('success'):
            user = session_response['user']
            logger.info(f"Session validated for user: {user.get('email', 'Unknown')}")
            
            response_data = {
                'authenticated': True,
                'user': {
                    'id': user.get('id'),
                    'google_id': user.get('google_id'),
                    'email': user.get('email'),
                    'name': user.get('name'),
                    'base_link': user.get('base_link')
                }
            }
            
            response = JsonResponse(response_data)
            
        else:
            logger.warning(f"Invalid session: {session_response.get('error', 'Unknown error')}")
            response = JsonResponse({
                'authenticated': False,
                'error': session_response.get('error', 'Invalid session')
            }, status=200)
            
            # Удаляем невалидную куку
            response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path='/',
                samesite='Lax'
            )
        
        # Добавляем CORS заголовки
        response["Access-Control-Allow-Origin"] = "http://k90908k8.beget.tech"
        response["Access-Control-Allow-Credentials"] = "true"
        
        return response
            
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}", exc_info=True)
        response = JsonResponse({
            'authenticated': False, 
            'error': 'Internal server error',
            'debug': str(e)
        }, status=500)
        response["Access-Control-Allow-Origin"] = "http://k90908k8.beget.tech"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    """Выход из системы"""
    try:
        data = json.loads(request.body)
        session_token = data.get('session_token')
        
        if session_token:
            logger.info(f"Deleting session: {session_token[:10]}...")
            php_client.delete_session(session_token)
            
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)