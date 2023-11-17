"""处理发票"""
import os
import fnmatch
import codecs
import shutil
import pendulum

from zipfile import ZipFile
from typing import List, Optional
from datetime import datetime

from fastapi import Request, UploadFile, APIRouter, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db.mongodb import MongoDB
from config.settings import Settings

from models.invoice_scanning import Invoice
from models.delete_file import delete_all_file

from models.store_msg import _error, _collections
from models.cookie import verify_cookie


_db_mongo = MongoDB()
_settings = Settings()

user_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


@user_routes.get("/{username}/{year}", response_class=HTMLResponse)
async def user(request: Request, username: str, year: str):
    """显示所有这个用户的发票"""
    # 删除所有PDF和ZIP文件
    delete_all_file()

    get_cookie = request.cookies.get("access-token")

    if get_cookie:
        c = verify_cookie(get_cookie)
        year_list = _db_mongo.latest_year(username)
        if username == c.username:
            # 发票讯息
            _collections.clear()
            invoice_data: list[dict] = list(_db_mongo.invoice_data(username).find({}))

            for check_each_invoice in invoice_data:
                dt = pendulum.parse(str(check_each_invoice["date"]))
                if str(dt.year) == year:
                    _collections.append(check_each_invoice)

            # ----------以下处理当年的文件----------
            amount_list: list[float] = []

            for each_invoice in _collections:
                amount_list.append(float(each_invoice["amount"]))
            response = templates.TemplateResponse(
                "user.html",
                {
                    "request": request,
                    "username": username,
                    "year": sorted(year_list, key=int),
                    "data": sorted(_collections, key=lambda x: x["date"]),
                    "total": f"{sum(amount_list):0.2f}",
                    "msg": _error,
                },
            )

            # 清除所有错误讯息
            _error.clear()
            return response
    return RedirectResponse(request.url_for("login"))


@user_routes.post("/{username}/{year}", response_class=RedirectResponse)
async def send_file(
    *,
    request: Request,
    files: List[UploadFile] = File(None),
    ids: List[Optional[str]] = None,
    username: str,
    year: str,
):
    """上传与下载发票功能"""
    try:
        # 下载区
        if ids:  # ids是checkbox如果激活会传回来为ids
            # 所有价格的综合
            get_total_amount = []

            # 解析每张发票并传送到服务器
            for _id in ids:
                # 取所有发票讯息
                pdf = _db_mongo.invoice_data(username).find_one({"_id": int(_id)})

                # 取所有发票的价格
                get_total_amount.append(float(pdf["amount"]))

                # 如果下载成功把download改为True
                _db_mongo.invoice_data(username).update_one(
                    {"_id": int(_id)}, {"$set": {"download": True}}
                )

                # 把文件临时村在服务器
                convert_date = pendulum.parse(str(pdf["date"]))
                name = f"{convert_date.to_date_string()}({pdf['_id']}-¥{pdf['amount']}).pdf"
                with open(name, "wb") as file:
                    file.write(codecs.decode(pdf["pdf"], "base64"))

            # 建立ZIP名字
            zip_name = f"{year}年-¥{sum(get_total_amount):0.2f}.zip"

            # 取所有PDF并存在ZIP里
            with ZipFile(zip_name, "w") as zip_file:
                # for _, _, pdf_file in os.walk("/"):
                for _, _, pdf_file in os.walk(_settings.LOCATION):
                    for name in pdf_file:
                        if fnmatch.fnmatch(name, "*.pdf"):
                            zip_file.write(name)
                            os.remove(name)
            # 转至download.py
            return RedirectResponse(request.url_for("download", file=zip_name))

        # 上传区
        _invoice = Invoice()
        for file in files:
            with open(file.filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                err_msg = _invoice.pdf_file(username=username, file=file.filename)
                os.remove(file.filename)
                if err_msg:
                    _error.append(err_msg)
            try:
                year: str = _invoice.date.year
            except:
                year = datetime.now().year

        return RedirectResponse(
            request.url_for("user", username=username, year=year), status_code=302
        )
    except FileNotFoundError:
        _error.append("没有文件上传")
        return RedirectResponse(
            request.url_for("user", username=username, year=year), status_code=302
        )
