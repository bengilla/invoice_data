import os

from fastapi import FastAPI, Request, File, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models.bill_scan import QRCode
from models.mongodb import MongoDB
from PIL import Image

_db = MongoDB()

app = FastAPI()
templates = Jinja2Templates(directory='templates')

def list_collection():
    list_collection = [x for x in _db.list_collections()]
    return sorted(list_collection)

@app.get("/", response_class=RedirectResponse)
async def index(request: Request):
    if len(list_collection()) != 0:
        num = list_collection()[0]
        return f"/{num}"
    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "list_col": list_collection(),
            }
        )

@app.get("/{num}", response_class=HTMLResponse)
async def first(request: Request, num: str):
    invoice_data = [x for x in _db.send_data(num).find({})]
    amount = [x['amount'] for x in invoice_data] 

    return templates.TemplateResponse(
        "index.html",
        {
        "request": request,
        "list_col": list_collection(),
        "data": invoice_data,
        "total": sum(amount)
        }
    )

@app.post("/{num}", response_class=RedirectResponse)
async def send_file(request: Request, image: UploadFile = File(None)):
    qrcode = QRCode()
    with Image.open(image.file) as im:
        im.save("invoice.png")

    file = 'invoice.png'
    qrcode.generate(file)
    os.remove(file)

    request_url = request.url_for("index")
    return RedirectResponse(request_url, status_code=status.HTTP_302_FOUND)
