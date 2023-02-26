import os

from fastapi import FastAPI, Request, File, UploadFile, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.bill_scan import QRCode
from models.mongodb import MongoDB
from PIL import Image

_db = MongoDB()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

qrcode = QRCode()


def list_collection():
    list_collection = [x for x in _db.list_collections()]
    return sorted(list_collection)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if len(list_collection()) == 0:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "list_col": list_collection(),
            },
        )
    else:
        num = list_collection()[0]
        response_url = request.url_for("first", num=num)
        return RedirectResponse(response_url, status_code=302)


@app.get("/{num}", response_class=HTMLResponse)
async def first(request: Request, num: str, message: str | None = Cookie(default=None)):
    invoice_data = [x for x in _db.send_data(num).find({})]
    amount = [x["amount"] for x in invoice_data]

    invoice_data.sort(key=lambda x: x["date"])

    if message:
        msg = message
    else:
        msg = ""

    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "list_col": list_collection(),
            "data": invoice_data,
            "total": round(sum(amount), 2),
            "msg": msg,
        },
    )
    response.delete_cookie(key="message")
    return response


@app.post("/", response_class=RedirectResponse)
async def send_file(
    request: Request,
    qrcode_image: UploadFile = File(None),
    pdf: UploadFile = File(None),
):
    with Image.open(qrcode_image.file) as im:
        im.save("invoice.png")

    file = "invoice.png"
    qrcode.generate(file)
    os.remove(file)

    request_url = request.url_for("index")
    return RedirectResponse(request_url, status_code=302)


@app.post("/{num}", response_class=RedirectResponse)
async def send_file(
    request: Request,
    qrcode_image: UploadFile = File(None),
    pdf: UploadFile = File(None),
):
    try:
        with Image.open(qrcode_image.file) as im:
            im.save("invoice.png")

        file = "invoice.png"
        qrcode.generate(file)
        os.remove(file)

        num = qrcode.month
        request_url = request.url_for("first", num=num)
        return RedirectResponse(request_url, status_code=302)
    except:
        request_url = request.url_for("index")
        response = RedirectResponse(request_url, status_code=302)
        response.set_cookie(key="message", value="Invoice is exists")
        return response
