import time
from typing import Annotated

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from models.manager import load_user
from models.password import Password
from models.error import _error
from models.jwt import encoded_jwt


login_routes = APIRouter()
templates = Jinja2Templates(directory="templates")

_password = Password()


@login_routes.get("/login")
async def login(request: Request):
    """Login Section"""

    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        return RedirectResponse(request.url_for("index"))
    return templates.TemplateResponse("login.html", {"request": request, "msg": _error})


@login_routes.post("/login", response_class=HTMLResponse)
async def login_data(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    # start = time.time()
    user = load_user(username)
    # end1 = time.time()
    # print(end1 - start)

    if username in user.user_collections:
        verify_password = _password.verify_password(password, user.password)

        # end2 = time.time()
        # print(end2 - end1)

        if user and verify_password:
            token = encoded_jwt(username)

            # end3 = time.time()
            # print(end3 - end2)

            redirect_url = "/"
            response = RedirectResponse(redirect_url)
            response.set_cookie(key="access-token", value=token, httponly=True)

            # end4 = time.time()
            # print(end4 - end3)

            return response
        _error.clear()
        _error.append("用户名或密码错误")
        return RedirectResponse(request.url_for("login"), status_code=302)
    _error.clear()
    _error.append("用户不存在，请注册")
    return RedirectResponse(request.url_for("login"), status_code=302)
