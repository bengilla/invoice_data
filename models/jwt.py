"""JWT功能"""
import jwt
from config.settings import Settings

_settings = Settings()


def encoded_jwt(username):
    encoded_jwt = jwt.encode(
        {"name": username}, _settings.JWT_SECRET_KEY, algorithm="HS256"
    )
    return encoded_jwt


def decoded_jwt(jwt_code):
    decoded_jwt = jwt.decode(jwt_code, _settings.JWT_SECRET_KEY, algorithms=["HS256"])
    return decoded_jwt["name"]
