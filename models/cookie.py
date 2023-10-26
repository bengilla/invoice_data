"""Cookie功能区"""
from datetime import datetime
from dataclasses import dataclass

from config.mongodb import MongoDB
from models.jwt import decoded_jwt

dt = datetime.now()

_db_mongo = MongoDB()


@dataclass
class Cookie:
    username: str
    year: int
    month: int


def verify_cookie(cookie) -> Cookie:
    """发回用户讯息和月份"""
    username: str = decoded_jwt(cookie)
    result = _db_mongo.year_n_month(username)

    if result["month"] == []:
        year = dt.year
        month: int = 0
    else:
        year: int = max(result["year"])
        month: int = max(result["month"])

    return Cookie(username=username, year=year, month=month)
