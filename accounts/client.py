import requests
import json
from ..myproject import settings

class PHPApiClient:
    def __init__(self):
        self.base_url = settings.PHP_API_URL
        self.secret = settings.PHP_API_SECRET
    
    def _make_request(self, action, data=None):
        headers = {
            'Authorization': f'Bearer {self.secret}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}?action={action}"
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"PHP API error: {response.text}")
    
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

php_client = PHPApiClient()
