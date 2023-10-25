from typing import Annotated

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

# from config.mongodb import MongoDB
from config.db import User

from models.password import Password
from models.error import _error


register_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@register_routes.get("/register")
async def register(request: Request):
    """Login Section"""

    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse(
        "register.html", {"request": request, "msg": _error}
    )


@register_routes.post("/register")
async def register_data(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    # code: Annotated[str, Form()],
):
    # _db_mongo = MongoDB()
    # code_list = _db_mongo.verify_code()

    _db = User()

    # if code in code_list:
    if _db.user_info(username) == None:
        _password = Password()
        password_hash = _password.get_password_hash(password)
        _db.user_register(username=username, password=password_hash)
        return RedirectResponse(request.url_for("index"), status_code=302)
    _error.clear()
    _error.append("用户已存在")
    return RedirectResponse(request.url_for("register"), status_code=302)
    # _error.clear()
    # _error.append("确认码错误")
    # return RedirectResponse(request.url_for("register"), status_code=302)
