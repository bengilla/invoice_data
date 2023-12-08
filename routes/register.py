"""用户注册区"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError

from db.mongodb import MongoDB

from db.db import Users

from models.password import Password


register_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_user_db():
    return Users()


def generate_password_hash(password: str):
    _password = Password()
    return _password.get_password_hash(password)


@register_routes.get("/register")
async def register(request: Request):
    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse("register.html", {"request": request})


@register_routes.post("/register")
async def register_data(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    code: str = Form(...),
    user_db: Users = Depends(get_user_db),
):
    _db_mongo = MongoDB()
    code_list = _db_mongo.verify_code()

    if code in code_list:
        try:
            password_hash = generate_password_hash(password)
            user_db.register(username=username, password=password_hash)
            return RedirectResponse(request.url_for("index"), status_code=302)
        except IntegrityError:
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error_msg": "用户已存在"},
            )
    return templates.TemplateResponse(
        "register.html", {"request": request, "error_msg": "确认码错误"}
    )
