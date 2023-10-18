"""Month Invoice Section"""
import os
import fnmatch
import codecs
import shutil

from zipfile import ZipFile

from fastapi import Request, UploadFile, APIRouter, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config.mongodb import MongoDB
from config.settings import Settings

from models.invoice_scanning import Invoice
from models.delete_file import delete_all_file


_db = MongoDB()
_settings = Settings()
_errors = []

month_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@month_routes.get("/month/{num}", response_class=HTMLResponse)
async def month(*, request: Request, num: str):
    """When previous pdf file is in db"""
    check_cookie = request.cookies.get("access-token")

    # delete zip file if zip in the server
    delete_all_file()

    if check_cookie:
        # all invoice information
        invoice_data: list[dict] = list(_db.invoice_data(num).find({}))
        # print(f"Invoice_data: {invoice_data}")
        # all amount
        amount: list[float] = [float(x["amount"]) for x in invoice_data]
        # print(f"Amount: {amount}")
        # all company name
        company: list(str) = []
        for c in invoice_data:
            if c["company"] not in company:
                company.append(c["company"])

        # all invoice sort by date
        invoice_data.sort(key=lambda x: x["date"])

        response = templates.TemplateResponse(
            "user.html",
            {
                "request": request,
                "list_col": _db.invoice_collections(),
                "data": invoice_data,
                "total": f"{sum(amount):0.2f}",
                "company": company,
                "msg": _errors,
            },
        )

        # clear the error message list
        _errors.clear()
        return response

    return RedirectResponse(request.url_for("login"))


@month_routes.post("/month/{num}", response_class=RedirectResponse)
async def send_file(
    *,
    request: Request,
    files: list[UploadFile] = File(None),
    ids: list[str | None] = None,
    num: str,
):
    """Upload pdf file when db has previous file"""
    try:
        # DOWNLOAD SECTION
        # ids are return from html checkbox
        if ids:
            # get all pdf amount to total
            get_total_amount = []

            # convert to single pdf file and save to server
            for _id in ids:
                # get info from db
                pdf = _db.invoice_data(num).find_one({"_id": int(_id)})

                # get total amount for download invoice
                get_total_amount.append(float(pdf["amount"]))

                # if download success turn download icon to True
                _db.invoice_data(num).update_one(
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
                # for _, _, pdf_file in os.walk("/"):
                for _, _, pdf_file in os.walk(_settings.LOCATION):
                    for name in pdf_file:
                        if fnmatch.fnmatch(name, "*.pdf"):
                            zip_file.write(name)
                            os.remove(name)
            # jump to download page and download zip file
            return RedirectResponse(request.url_for("download", file=zip_name))

        # UPLOAD SECTION
        # id not ids select to download, this function is upload pdf file
        _invoice = Invoice()
        for file in files:
            with open(file.filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                err_msg = _invoice.pdf_file(file.filename)
                os.remove(file.filename)
                if err_msg:
                    _errors.append(err_msg)
            try:
                num: str = _invoice.date.month
            except Exception as e:
                print(e)
                num = "0"

        return RedirectResponse(request.url_for("month", num=num), status_code=302)
    except FileNotFoundError:
        _errors.append("没有文件上传")
        return RedirectResponse(request.url_for("month", num=num), status_code=302)
