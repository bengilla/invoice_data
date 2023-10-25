from datetime import timedelta
from dataclasses import dataclass

from fastapi_login import LoginManager

from config.settings import Settings

from config.db import User

_settings = Settings()

manager = LoginManager(
    _settings.SECRET_KEY,
    "/login",
    use_cookie=True,
    use_header=False,
    default_expiry=timedelta(hours=2),
)


@dataclass
class UserData:
    username: str
    password: str


@manager.user_loader()
def load_user(username: str):
    _db = User()
    get_password = _db.user_info(username)
    return UserData(username=username, password=get_password)
