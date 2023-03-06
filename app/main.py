"""Invoice Calculate"""
import os
import fnmatch
import codecs
import shutil
import secrets
from zipfile import ZipFile

from fastapi import FastAPI, Request, File, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.settings import settings
from models.invoice_scanning import Invoice
from models.mongodb import MongoDB
from routes.download import download_routes
from routes.check import check_routes


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
    for file in os.listdir("."):
        if fnmatch.fnmatch(file, "*.zip") or fnmatch.fnmatch(file, "*.pdf"):
            os.remove(file)


@app.get("/", response_class=RedirectResponse)
async def index(request: Request, _=Depends(get_current_username)):
    """Upload pdf file when db is empty"""
    delete_all_file()  # delete all zip and pdf file
    count = list(_db.list_collections())
    if len(count) == 0:
        num = "0"
    else:
        num = count[0]
    return RedirectResponse(request.url_for("main", num=num), status_code=302)


@app.get("/month/{num}", response_class=HTMLResponse)
async def main(*, request: Request, _=Depends(get_current_username), num: str):
    """When previous pdf file is in db"""
    delete_all_file()  # delete all zip and pdf file

    # receive all invoice amount information
    invoice_data = list(_db.send_data(num).find({}))
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
    files: list[UploadFile] = File(None),
    ids: list[str | None] = None,
    _=Depends(get_current_username),
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

                get_total_amount.append(float(pdf["amount"]))

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
                err_msg = invoice.pdf_file(file.filename)
                os.remove(file.filename)
                if err_msg:
                    errors.append(err_msg)
            num: str = invoice.date.month

        return RedirectResponse(request.url_for("main", num=num), status_code=302)
    except FileNotFoundError:
        errors.append("没有文件上传")
        return RedirectResponse(request.url_for("main", num=num), status_code=302)


app.include_router(download_routes)
app.include_router(check_routes)
