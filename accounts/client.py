import requests

class PHPUserAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def create_user(self, login, password, email, telegram_id=None, body_link=None):
        url = f"{self.base_url}/api.php?action=create"
        payload = {
            "login": login,
            "password": password,
            "email": email,
            "telegram_id": telegram_id,
            "body_link": body_link,
        }
        return requests.post(url, json=payload).json()

    def get_user(self, login):
        url = f"{self.base_url}/api.php?action=get&login={login}"
        return requests.get(url).json()

    def update_user(self, login, **kwargs):
        url = f"{self.base_url}/api.php?action=update"
        data = {"login": login, **kwargs}
        return requests.post(url, json=data).json()

    def delete_user(self, login):
        url = f"{self.base_url}/api.php?action=delete&login={login}"
        return requests.get(url).json()
