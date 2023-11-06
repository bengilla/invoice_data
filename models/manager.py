"""使用LoginManager处理用户讯息并建立Cookie"""
from datetime import timedelta

from fastapi_login import LoginManager
from pydantic import BaseModel

from config.settings import Settings

from config.db import Users

_settings = Settings()

manager = LoginManager(
    _settings.SECRET_KEY,
    "/login",
    use_cookie=True,
    use_header=False,
    default_expiry=timedelta(hours=1),
)


class UserData(BaseModel):
    username: str
    password: str


@manager.user_loader()
def load_user(username: str) -> UserData:
    _db = Users()
    get_password = _db.user_info(username)
    return UserData(username=username, password=get_password)
