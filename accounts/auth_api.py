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
    """Валидация сессии с поддержкой mixed HTTP/HTTPS"""
    
    # CORS preflight
    if request.method == "OPTIONS":
        response = JsonResponse({})
        origin = request.headers.get('Origin', '')
        if origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-Token"
        return response
    
    try:
        # Способ 1: Ищем токен в кастомном заголовке
        session_token = request.headers.get('X-Session-Token')
        
        # Способ 2: Ищем в cookies
        if not session_token:
            session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        
        # Способ 3: Ищем в теле запроса
        if not session_token and request.body:
            try:
                body_data = json.loads(request.body)
                session_token = body_data.get('session_token')
            except:
                pass
        
        logger.info(f"Session token received: {'Yes' if session_token else 'No'}")
        
        if not session_token:
            response = JsonResponse({
                'authenticated': False, 
                'error': 'No session token provided',
                'debug': {
                    'headers': {k: v for k, v in request.headers.items() if 'token' in k.lower()},
                    'cookies': list(request.COOKIES.keys())
                }
            }, status=200)
        else:
            # Валидируем сессию через PHP API
            session_response = php_client.validate_session(session_token)
            
            if session_response.get('success'):
                user = session_response['user']
                response_data = {
                    'authenticated': True,
                    'user': {
                        'id': user.get('id'),
                        'email': user.get('email'),
                        'name': user.get('name'),
                        'base_link': user.get('base_link')
                    }
                }
                response = JsonResponse(response_data)
            else:
                response = JsonResponse({
                    'authenticated': False,
                    'error': session_response.get('error', 'Invalid session')
                }, status=200)
        
        # CORS заголовки
        origin = request.headers.get('Origin')
        if origin and origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        
        return response
            
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}", exc_info=True)
        response = JsonResponse({
            'authenticated': False, 
            'error': 'Internal server error'
        }, status=500)
        response["Access-Control-Allow-Origin"] = request.headers.get('Origin', 'http://k90908k8.beget.tech')
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