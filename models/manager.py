from datetime import timedelta

from fastapi_login import LoginManager

from config.settings import Settings
from config.mongodb import MongoDB

_settings = Settings()

manager = LoginManager(
    _settings.SECRET_KEY,
    "/login",
    use_cookie=True,
    use_header=False,
    default_expiry=timedelta(hours=2),
)


class User:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password


@manager.user_loader()
def load_user(username: str):
    _db = MongoDB()

    user_data: list[dict] = list(_db.user_data(username).find({}))
    password = [p["password"] for p in user_data]

    return User(username, password[0])
