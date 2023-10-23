import pendulum
from dataclasses import dataclass

from config.mongodb import MongoDB
from models.jwt import decoded_jwt

dt = pendulum.now()


@dataclass
class Cookie:
    username: str
    year: int
    month: int


def verify_cookie(cookie) -> Cookie:
    """return username and month_in_list"""
    _db = MongoDB()
    username: str = decoded_jwt(cookie)

    if _db.get_month_list(username) == []:
        year = dt.year
        month: int = 0
    else:
        year: int = max(_db.get_year_list(username))
        month: int = max(_db.get_month_list(username))

    return Cookie(username=username, year=year, month=month)
