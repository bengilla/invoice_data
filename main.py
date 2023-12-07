"""发票系统主页"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes.index import index_routes
from routes.login import login_routes
from routes.register import register_routes
from routes.user import user_routes
from routes.modify import modify_routes

from config.settings import Settings

_settings = Settings

app = FastAPI(title=_settings.TITLE, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(index_routes)
app.include_router(login_routes)
app.include_router(register_routes)
app.include_router(user_routes)
app.include_router(modify_routes)
