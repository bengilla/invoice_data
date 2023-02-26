import os

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.templating import Jinja2Templates
from models.bill_scan import QRCode
from models.mongodb import MongoDB
from PIL import Image

_db = MongoDB()

app = FastAPI()
templates = Jinja2Templates(directory='templates')

@app.get("/{num}")
async def index(request: Request):
    list_collection = [x for x in _db.list_collections()]
    invoice_data = [x for x in _db.send_data(1).find({})]
    
    amount = [x['amount'] for x in invoice_data] 

    return templates.TemplateResponse(
        "index.html",
        {
        "request": request,
        "list_col": sorted(list_collection),
        "data": invoice_data,
        "total": sum(amount)
        }
    )

@app.post("/")
async def send_file(request: Request, image: UploadFile = File(None)):
    qrcode = QRCode()
    with Image.open(image.file) as im:
        im.save("invoice.png")

    file = 'invoice.png'
    qrcode.generate(file)
    os.remove(file)
    return templates.TemplateResponse(
        "index.html", {"request": request})