import os, fnmatch
import codecs
import shutil
from typing import List
from config.settings import settings
from zipfile import ZipFile

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from models.bill_scan import Invoice
from models.mongodb import MongoDB


app = FastAPI(title=settings.TITLE)
app.mount("/statis", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_db = MongoDB()
invoice = Invoice()
errors = []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if len(_db.list_collections()) == 0:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "list_col": _db.list_collections()},
        )
    else:
        num: list[str] = _db.list_collections()[0]
        response_url = request.url_for("first", num=num)
        return RedirectResponse(response_url, status_code=302)


@app.get("/{num}", response_class=HTMLResponse)
async def first(request: Request, num: str):
    invoice_data = [x for x in _db.send_data(num).find({})]
    amount: float = [float(x["amount"]) for x in invoice_data]

    invoice_data.sort(key=lambda x: x["date"])

    if errors != 0:
        msg = errors

    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "list_col": _db.list_collections(),
            "data": invoice_data,
            "total": "{:0.2f}".format(sum(amount)),
            "msg": msg,
        },
    )
    errors.clear()
    return response


@app.post("/", response_class=RedirectResponse)
async def send_file(
    request: Request,
    files: List[UploadFile] = File(None),
):
    for file in files:
        with open(file.filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            err_msg = invoice.pdf_file(file.filename)
            os.remove(file.filename)
            if err_msg:
                errors.append(err_msg)
    num: str = invoice.month
    request_url = request.url_for("first", num=num)
    return RedirectResponse(request_url, status_code=302)


@app.post("/{num}", response_class=RedirectResponse)
async def send_file(
    *,
    request: Request,
    files: List[UploadFile] = File(None),
    ids: List[str | None] = None,
    num: str,
):
    try:
        if ids:
            get_amount = []
            for x in ids:
                pdf = _db.send_data(num).find_one({"_id": int(x)})

                date = pdf["date"]
                amount = pdf["amount"]
                code = pdf["pdf"]

                get_amount.append(float(amount))

                name = f"{date}[¥{amount}].pdf"
                with open(name, "wb") as f:
                    f.write(codecs.decode(code, "base64"))

            # total all the price
            output_total_amount = sum(get_amount)
            zip_name = f"{num}月-¥{'{:0.2f}'.format(output_total_amount)}.zip"
            zip_obj = ZipFile(zip_name, "w")

            for root, dir, files in os.walk("/"):
                for name in files:
                    if fnmatch.fnmatch(name, "*.pdf"):
                        zip_obj.write(name)
                        os.remove(name)

            zip_obj.close()

        else:
            for file in files:
                with open(file.filename, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                    err_msg = invoice.pdf_file(file.filename)
                    os.remove(file.filename)
                    if err_msg:
                        errors.append(err_msg)
            num: str = invoice.month

        request_url = request.url_for("first", num=num)
        return RedirectResponse(request_url, status_code=302)
    except:
        errors.append("No file upload")
        request_url = request.url_for("first", num=num)
        return RedirectResponse(request_url, status_code=302)
