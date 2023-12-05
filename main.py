"""发票系统主页"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config.settings import Settings

from routes.login import login_routes
from routes.register import register_routes
from routes.user import user_routes
from routes.modify import modify_routes

from models.cookie import verify_cookie


_settings = Settings

app = FastAPI(title=_settings.TITLE, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.route("/", methods=["GET", "POST"])
async def index(request: Request):
    if request.method == "GET":
        get_cookie = request.cookies.get("access-token")
        if get_cookie:
            cookie_response = verify_cookie(get_cookie)
            return RedirectResponse(
                request.url_for(
                    "user", username=cookie_response.username, year=cookie_response.year
                )
            )
        return RedirectResponse(request.url_for("login"))
    elif request.method == "POST":
        return templates.TemplateResponse("index.html", {"request": request})


app.include_router(login_routes)
app.include_router(register_routes)
app.include_router(user_routes)
app.include_router(modify_routes)
