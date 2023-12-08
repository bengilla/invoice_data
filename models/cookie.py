"""Cookie功能区"""
from datetime import datetime
from pydantic import BaseModel

from db.db import Invoices
from models.jwt import decoded_jwt


class Cookie(BaseModel):
    username: str
    year: int


def verify_cookie(cookie) -> Cookie:
    """发回用户讯息,年份和月份"""
    _db = Invoices()
    _dt = datetime.now()
    username: str = decoded_jwt(cookie)
    latest_year = _db.year_invoice(username)

    if latest_year == []:
        year: int = _dt.year
    else:
        # year: int = max(latest_year)
        year: int = max(latest_year)

    return Cookie(username=username, year=year)
