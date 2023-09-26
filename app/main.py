"""Invoice Calculate"""
import os
import fnmatch
import codecs
import shutil

from zipfile import ZipFile

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from models.invoice_scanning import Invoice
from app.config.mongodb import MongoDB
from routes.download import download_routes
from routes.check import check_routes

app = FastAPI(title=settings.TITLE)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_db = MongoDB()
_invoice = Invoice()
_errors = []


def delete_all_file():
    """Delete pdf and zip function"""
    for file in os.listdir("."):
        if fnmatch.fnmatch(file, "*.zip") or fnmatch.fnmatch(file, "*.pdf"):
            os.remove(file)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Upload pdf file when db is empty"""
    # delete zip file if zip in the server
    delete_all_file()

    # get last month in list and get the number
    last_month_in_list = _db.list_collections()[-1]

    return RedirectResponse(
        request.url_for("main", num=last_month_in_list), status_code=302
    )


@app.get("/month/{num}", response_class=HTMLResponse)
async def main(*, request: Request, num: str):
    """When previous pdf file is in db"""
    # delete zip file if zip in the server
    delete_all_file()

    # all invoice information
    invoice_data = list(_db.send_data(num).find({}))
    # all amount
    amount = [float(x["amount"]) for x in invoice_data]
    # all company name
    company = set([x["company"] for x in invoice_data])

    # sort by date
    invoice_data.sort(key=lambda x: x["date"])

    response = templates.TemplateResponse(
        "user.html",
        {
            "request": request,
            "list_col": _db.list_collections(),
            "data": invoice_data,
            "total": f"{sum(amount):0.2f}",
            "company": company,
            "msg": _errors,
        },
    )

    # clear the error message list
    _errors.clear()
    return response


@app.post("/month/{num}", response_class=RedirectResponse)
async def send_file(
    *,
    request: Request,
    files: list[UploadFile] = File(None),
    ids: list[str | None] = None,
    num: str,
):
    """Upload pdf file when db has previous file"""
    try:
        # ids are return from html checkbox
        if ids:
            # get all pdf amount to total
            get_total_amount = []

            # convert to single pdf file and save to server
            for _id in ids:
                # get info from db
                pdf = _db.send_data(num).find_one({"_id": int(_id)})

                # get total amount for download invoice
                get_total_amount.append(float(pdf["amount"]))

                # if download success turn download icon to True
                _db.send_data(num).update_one(
                    {"_id": int(_id)}, {"$set": {"download": True}}
                )

                # save file to the server
                name = f"{pdf['date']}({pdf['_id']}-¥{pdf['amount']}).pdf"
                with open(name, "wb") as file:
                    file.write(codecs.decode(pdf["pdf"], "base64"))

            # download pdf and save to zip
            zip_name = f"{num}月-¥{sum(get_total_amount):0.2f}.zip"

            # search pdf on server and zip all the file
            with ZipFile(zip_name, "w") as zip_file:
                for _, _, pdf_file in os.walk("/"):
                    for name in pdf_file:
                        if fnmatch.fnmatch(name, "*.pdf"):
                            zip_file.write(name)
                            os.remove(name)

            # jump to download page and download zip file
            return RedirectResponse(
                request.url_for("download", file=zip_name), status_code=302
            )

        # id not ids select to download, this function is upload pdf file
        for file in files:
            with open(file.filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                err_msg = _invoice.pdf_file(file.filename)
                os.remove(file.filename)
                if err_msg:
                    _errors.append(err_msg)
            try:
                num: str = _invoice.date.month
            except Exception:
                num = "0"

        return RedirectResponse(request.url_for("main", num=num), status_code=302)
    except FileNotFoundError:
        _errors.append("没有文件上传")
        return RedirectResponse(request.url_for("main", num=num), status_code=302)


app.include_router(download_routes)
app.include_router(check_routes)
