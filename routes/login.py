"""用户登入系统区"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from models.manager import load_user
from models.jwt import encoded_jwt
from models.password import Password


login_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


def generate_user_info(username: str, password: str):
    _password = Password()
    user = load_user(username)
    verify_password = _password.verify_password(password, user.password)
    return verify_password


@login_routes.get("/login", response_class=RedirectResponse)
async def login(request: Request):
    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse("login.html", {"request": request})


@login_routes.post("/login", response_class=RedirectResponse)
async def login_data(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    try:
        user_verify = generate_user_info(username=username, password=password)
        if user_verify:
            token = encoded_jwt(username)

            redirect_url = "/"
            response = RedirectResponse(redirect_url)
            response.set_cookie(key="access-token", value=token, httponly=True)

            return response
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_msg": "用户名或密码错误"},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_msg": "用户不存在，请注册"},
        )
