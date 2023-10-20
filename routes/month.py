"""Month Invoice Section"""
import os
import fnmatch
import codecs
import shutil
import pendulum

from zipfile import ZipFile

from fastapi import Request, UploadFile, APIRouter, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config.mongodb import MongoDB
from config.settings import Settings

from models.invoice_scanning import Invoice
from models.delete_file import delete_all_file
from models.jwt import decoded_jwt


_db = MongoDB()
_settings = Settings()
_errors = []

user_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@user_routes.get("/{username}/{num}", response_class=HTMLResponse)
async def user(request: Request, username: str, num: str):
    """When previous pdf file is in db"""
    # delete zip file if zip in the server
    delete_all_file()

    get_cookie = request.cookies.get("access-token")

    if get_cookie:
        check_user = decoded_jwt(get_cookie)
        if username == check_user:
            # all invoice information
            invoice_data: list[dict] = list(_db.invoice_data(username).find({}))
            # print(f"Invoice_data: {invoice_data}")

            store_invoice: list[dict] = []
            store_month: list[str] = []

            for each_invoice in invoice_data:
                each_date = pendulum.from_format(each_invoice["date"], "YYYY-MM-DD")
                if num == str(each_date.month):
                    store_invoice.append(each_invoice)

                # get all date list
                if str(each_date.month) not in store_month:
                    store_month.append(str(each_date.month))

            # second part
            amount_list: list[float] = []
            company_list: list[str] = []

            for invoice in store_invoice:
                # get all amount
                amount_list.append(float(invoice["amount"]))

                # get all company name
                if invoice["company"] not in company_list:
                    company_list.append(invoice["company"])

            response = templates.TemplateResponse(
                "user.html",
                {
                    "request": request,
                    "username": username,
                    "list_col": sorted(store_month, key=int),
                    "data": sorted(store_invoice, key=lambda x: x["date"]),
                    "total": f"{sum(amount_list):0.2f}",
                    "company": company_list,
                    "msg": _errors,
                },
            )

            # clear the error message list
            _errors.clear()
            return response
            # print(f"Amount: {amount_list}")
            # print(f"Company: {company_list}")
            # print(f"Date: {month_list}")
    return RedirectResponse(request.url_for("login"))


@user_routes.post("/{username}/{num}", response_class=RedirectResponse)
async def send_file(
    *,
    request: Request,
    files: list[UploadFile] = File(None),
    ids: list[str | None] = None,
    username: str,
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
                pdf = _db.invoice_data(username).find_one({"_id": int(_id)})

                # get total amount for download invoice
                get_total_amount.append(float(pdf["amount"]))

                # if download success turn download icon to True
                _db.invoice_data(username).update_one(
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
                err_msg = _invoice.pdf_file(username=username, file=file.filename)
                os.remove(file.filename)
                if err_msg:
                    _errors.append(err_msg)
            try:
                num: str = _invoice.date.month
            except:
                num = "0"

        return RedirectResponse(
            request.url_for("user", username=username, num=num), status_code=302
        )
    except FileNotFoundError:
        _errors.append("没有文件上传")
        return RedirectResponse(
            request.url_for("user", username=username, num=num), status_code=302
        )
