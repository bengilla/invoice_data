"""发票系统主页"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config.settings import Settings

from routes.download import download_routes
from routes.check import check_routes
from routes.login import login_routes
from routes.user import user_routes
from routes.register import register_routes

from models.delete_file import delete_all_file
from models.cookie import verify_cookie


_settings = Settings()

app = FastAPI(title=_settings.TITLE, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("startup")
async def startup():
    # 删除全部错误与删除所有文件 (ZIP和PDF)
    delete_all_file()


@app.get("/", response_class=RedirectResponse)
async def index(request: Request):
    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        c = verify_cookie(get_cookie)
        return RedirectResponse(
            request.url_for("user", username=c.username, year=c.year)
        )
    return RedirectResponse(request.url_for("login"))


@app.post("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(login_routes)
app.include_router(register_routes)
app.include_router(download_routes)
app.include_router(check_routes)
app.include_router(user_routes)
