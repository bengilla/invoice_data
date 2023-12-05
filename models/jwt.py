"""JWT功能"""
import jwt
from config.settings import Settings

_settings = Settings


def encoded_jwt(username):
    encoded = jwt.encode(
        {"name": username}, _settings.JWT_SECRET_KEY, algorithm="HS256"
    )
    return encoded


def decoded_jwt(jwt_code):
    decoded = jwt.decode(jwt_code, _settings.JWT_SECRET_KEY, algorithms=["HS256"])
    return decoded["name"]
