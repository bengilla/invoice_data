from typing import Annotated

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config.mongodb import MongoDB

from models.password import Password
from models.error import _error
from models.cookie import verify_cookie


register_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@register_routes.get("/register")
async def register(request: Request):
    """Login Section"""
    _error.clear()

    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        c = verify_cookie(get_cookie)
        return RedirectResponse(
            request.url_for("user", username=c.username, month=c.month)
        )
    return templates.TemplateResponse(
        "register.html", {"request": request, "msg": _error}
    )


@register_routes.post("/register")
async def register_data(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    code: Annotated[str, Form()],
):
    _db = MongoDB()
    user_list = _db.user_collection()
    code_list = _db.verify_code()

    if code in code_list:
        if username.strip() not in user_list:
            _password = Password()

            user_info = {"password": _password.get_password_hash(password)}
            _db.user_data(str(username.strip())).insert_one(user_info)
            return RedirectResponse(request.url_for("index"), status_code=302)
        _error.clear()
        _error.append("用户已存在")
        return RedirectResponse(request.url_for("register"), status_code=302)
    _error.clear()
    _error.append("确认码错误")
    return RedirectResponse(request.url_for("register"), status_code=302)
