from typing import Annotated
from datetime import timedelta
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi_login import LoginManager
from config.settings import Settings

_settings = Settings()

login_routes = APIRouter()
templates = Jinja2Templates(directory="templates")

DB = {"users": {"beng@mail.com": {"name": "Bengilla", "password": "1234"}}}

SECRET = _settings.SECRET_KEY
manager = LoginManager(
    SECRET,
    "/login",
    use_cookie=True,
    use_header=False,
    default_expiry=timedelta(hours=12),
)


@manager.user_loader()
def query_user(user_id: str):
    """
    Get a user from the db
    :param user_id: E-Mail of the user
    :return: None or the user object
    """
    # test_user = DB["users"].get(user_id)
    # print(test_user)
    return DB["users"].get(user_id)


@login_routes.get("/login")
async def login(request: Request):
    """Login Section"""
    return templates.TemplateResponse("login.html", {"request": request})


@login_routes.post("/login")
async def login_data(email: Annotated[str, Form()], password: Annotated[str, Form()]):
    # email = data.username
    # password = data.password

    # user = query_user(email)
    # if not user:
    #     raise InvalidCredentialsException
    # elif password != user["password"]:
    #     raise InvalidCredentialsException

    # access_token = manager.create_access_token(data={"sub": email})
    # manager.set_cookie(response, access_token)
    # return {"access_token": access_token}
    return {"email": email, "password": password}
