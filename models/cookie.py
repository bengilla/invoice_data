"""Cookie功能区"""
import pendulum
from pydantic import BaseModel

from db.mongodb import MongoDB
from models.jwt import decoded_jwt

dt = pendulum.now()


class Cookie(BaseModel):
    username: str
    year: int


def verify_cookie(cookie) -> Cookie:
    """发回用户讯息,年份和月份"""
    _db_mongo = MongoDB()
    username: str = decoded_jwt(cookie)
    latest_year = _db_mongo.latest_year(username)

    if latest_year == []:
        year: int = dt.year
    else:
        year: int = max(latest_year)

    return Cookie(username=username, year=year)
