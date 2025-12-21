import jwt
from django.conf import settings

def create_jwt(user_id: int, pub_id: int) -> str:
    payload = {
        "uid": user_id,
        "pub_id": pub_id,
        "iss": settings.JWT_ISSUER,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm="HS256"
    )

    return token
