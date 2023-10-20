"""Invoice Calculate"""
import pendulum

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config.settings import Settings
from config.mongodb import MongoDB

from routes.download import download_routes
from routes.check import check_routes
from routes.login import login_routes
from routes.month import user_routes
from routes.register import register_routes

from models.delete_file import delete_all_file
from models.error import _error
from models.jwt import decoded_jwt


_settings = Settings()

app = FastAPI(title=_settings.TITLE, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=RedirectResponse)
async def index(request: Request):
    """Upload pdf file when db is empty"""
    # delete zip file if zip in the server
    delete_all_file()
    _error.clear()

    check_cookie = request.cookies.get("access-token")
    if check_cookie:
        username = decoded_jwt(check_cookie)

        _db = MongoDB()

        # get data from user date
        invoice_data: list[dict] = list(_db.invoice_data(username).find({}))

        # get last month in list and get the number
        date_list: list[str] = []
        for d in invoice_data:
            get_month = pendulum.from_format(d["date"], "YYYY-MM-DD")
            if get_month.month not in date_list:
                date_list.append(get_month.month)
        if date_list == []:
            month_in_list: str = "0"
        else:
            month_in_list: str = max(date_list)

        return RedirectResponse(
            request.url_for("user", username=username, num=month_in_list)
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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", port=int(_settings.PORT), host="0.0.0.0", reload=True)
