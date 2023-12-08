"""修改数据系统区"""
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from db.db import Invoices
from models.cookie import verify_cookie


modify_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_invoice_db():
    return Invoices()


@modify_routes.get("/{username}/modify/{invoice_id}", response_class=HTMLResponse)
async def modify(
    request: Request,
    username: str,
    invoice_id: int,
    invoice_db: Invoices = Depends(get_invoice_db),
):
    get_cookie = request.cookies.get("access-token")
    if get_cookie:
        user_cookie = verify_cookie(get_cookie)
        if user_cookie.username == username:
            each_data = invoice_db.each_invoice(invoice_id)
            return templates.TemplateResponse(
                "modify.html", {"request": request, "data": each_data}
            )
    return RedirectResponse(request.url_for("login"))


@modify_routes.post("/{username}/modify/{invoice_id}", response_class=RedirectResponse)
async def login_data(
    request: Request,
    username: str,
    invoice_id: int,
    reason: Optional[str] = Form(),
    note: Optional[str] = Form(),
    invoice_db: Invoices = Depends(get_invoice_db),
):
    year = invoice_db.year_invoice(username)

    invoice_db.modify(invoice_id=invoice_id, reason=reason, note=note)

    return RedirectResponse(
        request.url_for("user", username=username, year=max(year)), status_code=302
    )
