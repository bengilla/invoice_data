"""用户登入系统区"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from models.manager import load_user
from models.jwt import encoded_jwt
from models.password import Password
from models.store_msg import _error


login_routes = APIRouter()
templates = Jinja2Templates(directory="templates")

_password = Password()


@login_routes.get("/login")
async def login(request: Request):
    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse("login.html", {"request": request, "msg": _error})


@login_routes.post("/login", response_class=HTMLResponse)
async def login_data(
    request: Request,
    username: str = Form(),
    password: str = Form(),
):
    try:
        user = load_user(username)
        verify_password = _password.verify_password(password, user.password)

        if verify_password:
            token = encoded_jwt(username)

            redirect_url = "/"
            response = RedirectResponse(redirect_url)
            response.set_cookie(key="access-token", value=token, httponly=True)

            return response
        _error.append("用户名或密码错误")
        return RedirectResponse(request.url_for("login"), status_code=302)
    except:
        _error.append("用户不存在，请注册")
        return RedirectResponse(request.url_for("login"), status_code=302)
