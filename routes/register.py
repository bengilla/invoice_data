"""用户注册区"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError

from config.mongodb import MongoDB

from config.db import Users

from models.password import Password
from models.store_msg import _error


register_routes = APIRouter()
templates = Jinja2Templates(directory="templates")

_db_mongo = MongoDB()


@register_routes.get("/register")
async def register(request: Request):
    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse(
        "register.html", {"request": request, "msg": _error}
    )


@register_routes.post("/register")
async def register_data(
    request: Request,
    username: str = Form(),
    password: str = Form(),
    code: str = Form(),
):
    code_list = _db_mongo.verify_code()

    _db = Users()

    if code in code_list:
        try:
            _password = Password()
            password_hash = _password.get_password_hash(password)
            _db.register(username=username, password=password_hash)
            return RedirectResponse(request.url_for("index"), status_code=302)
        except IntegrityError:
            _error.clear()
            _error.append("用户已存在")
            return RedirectResponse(request.url_for("register"), status_code=302)
    _error.clear()
    _error.append("确认码错误")
    return RedirectResponse(request.url_for("register"), status_code=302)
