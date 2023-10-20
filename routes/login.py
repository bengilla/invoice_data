from typing import Annotated

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from config.mongodb import MongoDB

from models.manager import load_user
from models.password import Password
from models.error import _error
from models.jwt import encoded_jwt


login_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@login_routes.get("/login")
async def login(request: Request):
    """Login Section"""
    return templates.TemplateResponse("login.html", {"request": request, "msg": _error})


@login_routes.post("/login", response_class=HTMLResponse)
async def login_data(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    _db = MongoDB()
    user_list = _db.user_collection()

    if username in user_list:
        _password = Password()
        user = load_user(username)
        verify_password = _password.verify_password(password, user.password)

        if user and verify_password:
            token = encoded_jwt(username)

            redirect_url = "/"
            response = RedirectResponse(redirect_url)
            response.set_cookie(key="access-token", value=token, httponly=True)
            return response
    _error.clear()
    _error.append("用户名或密码错误")
    return RedirectResponse(request.url_for("login"), status_code=302)
