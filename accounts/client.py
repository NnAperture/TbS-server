import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class PHPApiClient:
    def __init__(self):
        self.base_url = settings.PHP_API_URL
        self.secret = settings.PHP_API_SECRET
        self.session = requests.Session()
        
        # Настройка сессии
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.secret}'
        })
        
        # Таймауты для запросов
        self.timeout = 30
    
    def _make_request(self, action, data=None):
        try:
            url = f"{self.base_url}?action={action}"
            
            logger.debug(f"Making request to PHP API: {url}")
            logger.debug(f"Request data: {data}")
            
            response = self.session.post(
                url, 
                json=data, 
                timeout=self.timeout,
                verify=True  # Включаем проверку SSL
            )
            
            logger.debug(f"PHP API response status: {response.status_code}")
            logger.debug(f"PHP API response text: {response.text}")
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to PHP API failed: {str(e)}")
            raise Exception(f"PHP API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise Exception(f"Invalid JSON response from PHP API")
    
    def get_or_create_user(self, google_id, base_link, email=None, name=None):
        data = {
            'google_id': google_id,
            'base_link': base_link,
            'email': email,
            'name': name
        }
        return self._make_request('get_user_by_google', data)
    
    def create_session(self, user_id):
        data = {'user_id': user_id}
        return self._make_request('create_session', data)
    
    def validate_session(self, session_token):
        data = {'session_token': session_token}
        return self._make_request('validate_session', data)
    
    def delete_session(self, session_token):
        data = {'session_token': session_token}
        return self._make_request('delete_session', data)

# Глобальный экземпляр клиента
php_client = PHPApiClient()