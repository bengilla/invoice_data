from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from models.cookie import verify_cookie

index_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@index_routes.route("/", methods=["GET", "POST"])
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
