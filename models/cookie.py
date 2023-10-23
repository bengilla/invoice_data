from config.mongodb import MongoDB
from models.jwt import decoded_jwt


def verify_cookie(cookie) -> list[str, int]:
    """return username and month_in_list"""
    _db = MongoDB()
    username: str = decoded_jwt(cookie)

    if _db.get_month_list(username) == []:
        month_in_list: int = 0
    else:
        month_in_list: int = max(_db.get_month_list(username))
    return [username, month_in_list]
