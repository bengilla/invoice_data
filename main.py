"""Invoice Calculate"""
import os
import fnmatch
import codecs
import shutil
import secrets
from typing import List
from zipfile import ZipFile

from fastapi import FastAPI, Request, File, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.settings import settings
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
    """Basic HTTPAuth"""
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
    """Delete pdf and zip function"""
    for _root, _dir, files in os.walk("/"):
        for name in files:
            if fnmatch.fnmatch(name, "*.zip"):
                os.remove(name)
            if fnmatch.fnmatch(name, "*.pdf"):
                os.remove(name)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _=Depends(get_current_username)):
    """Upload pdf file when db is empty"""
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
    """Upload pdf file when db is empty"""
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
    """When previous pdf file is in db"""
    delete_all_file()  # delete all zip and pdf file

    # receive all invoice amount information
    invoice_data = [x for x in _db.send_data(num).find({})]
    amount = [float(x["amount"]) for x in invoice_data]

    # sort by date
    invoice_data.sort(key=lambda x: x["date"])

    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "list_col": _db.list_collections(),
            "data": invoice_data,
            "total": f"{sum(amount):0.2f}",
            "msg": errors,
        },
    )
    # clear the error message list
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
    """Upload pdf file when db has previous file"""
    try:
        # ids are return from html checkbox
        if ids:
            get_amount = []
            for _id in ids:
                # get info from db
                pdf = _db.send_data(num).find_one({"_id": int(_id)})

                id_number = pdf["_id"]
                date = pdf["date"]
                amount = pdf["amount"]
                code = pdf["pdf"]

                get_amount.append(float(amount))

                # save file to the server
                name = f"{date}({id_number}-¥{amount}).pdf"
                with open(name, "wb") as file:
                    file.write(codecs.decode(code, "base64"))

            # total all the price
            output_total_amount = sum(get_amount)

            # zip
            zip_name = f"{num}月-¥{output_total_amount:0.2f}.zip"

            # search pdf on server and zip all the file
            with ZipFile(zip_name, "w") as file_zip:
                for _root, _dir, files in os.walk("/"):
                    for name in files:
                        if fnmatch.fnmatch(name, "*.pdf"):
                            file_zip.write(name)
                            os.remove(name)

            # jump to download page and download zip file
            return RedirectResponse(
                request.url_for("download", file=zip_name), status_code=302
            )
        else:
            # upload pdf file section
            for file in files:
                with open(file.filename, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                    err_msg = invoice.pdf_file(file.filename)
                    os.remove(file.filename)
                    if err_msg:
                        errors.append(err_msg)
            num: str = invoice.month

        return RedirectResponse(request.url_for("main", num=num), status_code=302)
    except FileNotFoundError:
        errors.append("No file upload")
        return RedirectResponse(request.url_for("main", num=num), status_code=302)


@app.get("/download/{file}", response_class=FileResponse)
async def download(*, _=Depends(get_current_username), file: str):
    """Download file section"""
    return FileResponse(path=file, filename=file)


@app.get("/check/")
async def check(_=Depends(get_current_username)):
    """Check all zip and pdf file"""

    def count_size(size):
        if size < 1000:
            return f"{size} bytes"
        elif 100000 > size >= 1000:
            return f"{round(size / 1000, 2)} KB"
        else:
            return f"{round(size / 1000000, 2)} MB"

    def file_info(file, size):
        data = {"file_name": file, "file_size": size}
        return data

    file_list = []
    for _root, _dir, files in os.walk("/"):
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
