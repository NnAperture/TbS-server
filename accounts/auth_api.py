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
    """Валидация сессии"""
    
    # CORS preflight
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "http://k90908k8.beget.tech"
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Session-Token"
        return response
    
    try:
        # 1. Проверяем токен в заголовке X-Session-Token
        session_token = request.headers.get('X-Session-Token')
        
        # 2. Если нет в заголовке, проверяем в теле запроса
        if not session_token and request.body:
            try:
                body_data = json.loads(request.body)
                session_token = body_data.get('session_token')
            except:
                pass
        
        logger.info(f"Session token received: {'Yes' if session_token else 'No'}")
        
        if not session_token:
            return JsonResponse({
                'authenticated': False,
                'error': 'No session token provided'
            }, status=200)
        
        # Валидируем сессию через PHP API
        session_response = php_client.validate_session(session_token)
        
        if session_response.get('success'):
            user = session_response['user']
            logger.info(f"Session validated for user: {user.get('email', 'Unknown')}")
            
            return JsonResponse({
                'authenticated': True,
                'user': {
                    'id': user.get('id'),
                    'email': user.get('email'),
                    'name': user.get('name'),
                    'base_link': user.get('base_link')
                }
            })
        else:
            logger.warning(f"Invalid session: {session_response.get('error')}")
            return JsonResponse({
                'authenticated': False,
                'error': session_response.get('error', 'Invalid session')
            }, status=200)
            
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}", exc_info=True)
        return JsonResponse({
            'authenticated': False,
            'error': 'Internal server error'
        }, status=500)

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