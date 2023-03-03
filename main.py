import os, fnmatch
import codecs
import shutil
import secrets
from typing import List
from config.settings import settings
from zipfile import ZipFile

from fastapi import FastAPI, Request, File, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from models.bill_scan import Invoice
from models.mongodb import MongoDB


app = FastAPI(title=settings.TITLE)
app.mount("/statis", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

_db = MongoDB()
invoice = Invoice()
errors = []


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(settings.USERNAME, encoding="utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(settings.PASSWORD, encoding="utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username and password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def delete_all_file():
    for root, dir, files in os.walk("/"):
        for name in files:
            if fnmatch.fnmatch(name, "*.zip"):
                os.remove(name)
            if fnmatch.fnmatch(name, "*.pdf"):
                os.remove(name)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _=Depends(get_current_username)):
    """When all data is empty"""
    delete_all_file()  # delete all zip and pdf file

    if len(_db.list_collections()) == 0:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "list_col": _db.list_collections()},
        )
    else:
        num: list[str] = _db.list_collections()[0]
        return RedirectResponse(request.url_for("main", num=num), status_code=302)


@app.post("/", response_class=RedirectResponse)
async def send_file(
    request: Request,
    files: List[UploadFile] = File(None),
    _=Depends(get_current_username),
):
    for file in files:
        with open(file.filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            err_msg = invoice.pdf_file(file.filename)
            os.remove(file.filename)
            if err_msg:
                errors.append(err_msg)
    num: str = invoice.month
    return RedirectResponse(request.url_for("main", num=num), status_code=302)


@app.get("/month/{num}", response_class=HTMLResponse)
async def main(*, request: Request, _=Depends(get_current_username), num: str):
    """When data is valid"""
    delete_all_file()  # delete all zip and pdf file

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


@app.post("/month/{num}", response_class=RedirectResponse)
async def send_file(
    *,
    request: Request,
    files: List[UploadFile] = File(None),
    ids: List[str | None] = None,
    _=Depends(get_current_username),
    num: str,
):
    try:
        if ids:
            get_amount = []
            for x in ids:
                pdf = _db.send_data(num).find_one({"_id": int(x)})

                id_number = pdf["_id"]
                date = pdf["date"]
                amount = pdf["amount"]
                code = pdf["pdf"]

                get_amount.append(float(amount))

                name = f"{date}({id_number}-¥{amount}).pdf"
                with open(name, "wb") as f:
                    f.write(codecs.decode(code, "base64"))

            # total all the price
            output_total_amount = sum(get_amount)
            # zip
            zip_name = f"{num}月-¥{'{:0.2f}'.format(output_total_amount)}.zip"

            with ZipFile(zip_name, "w") as file_zip:
                for root, dir, files in os.walk("/"):
                    for name in files:
                        if fnmatch.fnmatch(name, "*.pdf"):
                            file_zip.write(name)
                            os.remove(name)
            return RedirectResponse(
                request.url_for("download", file=zip_name), status_code=302
            )
        else:
            for file in files:
                with open(file.filename, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                    err_msg = invoice.pdf_file(file.filename)
                    os.remove(file.filename)
                    if err_msg:
                        errors.append(err_msg)
            num: str = invoice.month

        return RedirectResponse(request.url_for("main", num=num), status_code=302)
    except:
        errors.append("No file upload")
        return RedirectResponse(request.url_for("main", num=num), status_code=302)


@app.get("/download/{file}", response_class=FileResponse)
async def download(*, _=Depends(get_current_username), file: str):
    """Download file section"""
    return FileResponse(path=file, filename=file)


@app.get("/check/")
async def check(_=Depends(get_current_username)):
    """check all zip and pdf file"""

    def count_size(size):
        if size < 1000:
            return f"{size} bytes"
        elif size >= 1000 and size < 100000:
            return f"{round(size / 1000, 2)} KB"
        else:
            return f"{round(size / 1000000, 2)} MB"

    def file_info(file, size):
        data = {"filename": file, "filesize": size}
        return data

    file_list = []
    for root, dir, files in os.walk("/"):
        for name in files:
            if fnmatch.fnmatch(name, "*.zip"):
                get_size = os.path.getsize(name)
                output_data = file_info(name, count_size(get_size))
                file_list.append(output_data)
            if fnmatch.fnmatch(name, "*.pdf"):
                get_size = os.path.getsize(name)
                output_data = file_info(name, count_size(get_size))
                file_list.append(output_data)

    return {"message": file_list}
