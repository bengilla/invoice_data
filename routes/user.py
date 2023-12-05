"""处理发票"""
import os
import shutil
import base64

from zipfile import ZipFile
from typing import List
from datetime import datetime

from fastapi import Request, UploadFile, APIRouter, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from db.db import Users, Invoices

from models.invoice_scanning import InvoiceScan
from models.delete_file import delete_file

from models.store_msg import _error, _collections
from models.cookie import verify_cookie

from models.excel import excel

user_routes = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_user_db():
    return Users()


def get_invoice_db():
    return Invoices()


@user_routes.get("/{username}/{year}", response_class=HTMLResponse)
async def user(
    request: Request,
    username: str,
    year: str,
    user_db: Users = Depends(get_user_db),
    invoice_db: Invoices = Depends(get_invoice_db),
):
    """显示所有这个用户的发票"""
    # 删除所有PDF和ZIP文件
    delete_file(username)

    get_cookie = request.cookies.get("access-token")

    if get_cookie:
        verify = verify_cookie(get_cookie)

        # 获取所有用户的发票
        current_user = user_db.user_info(username)
        user_invoice = current_user.invoice

        # 获取所有发票的年份
        year_list = invoice_db.year_invoice(username)

        if username == verify.username:
            # 发票讯息
            _collections.clear()
            amount: list[float] = []

            for each_invoice in user_invoice:
                dt = each_invoice.date
                if str(dt.year) == year:
                    _collections.append(each_invoice)
                    amount.append(each_invoice.amount)

            response = templates.TemplateResponse(
                "user.html",
                {
                    "request": request,
                    "username": username,
                    "year": sorted(year_list, key=int),
                    "data": sorted(_collections, key=lambda x: x.date),
                    "total": f"{sum(amount):0.2f}",
                    "msg": _error,
                },
            )

            # 清除所有错误讯息
            _error.clear()
            return response
    return RedirectResponse(request.url_for("login"))


@user_routes.post("/{username}/{year}")
async def send_file(
    username: str,
    year: str,
    request: Request,
    files: List[UploadFile] = File(None),
    ids: List[str] = None,
    user_db: Users = Depends(get_user_db),
    invoice_db: Invoices = Depends(get_invoice_db),
):
    """上传与下载发票功能"""
    try:
        # ---------- 下载区 ----------
        PATH = os.getcwd() + "/user_file/"
        USER_PATH = PATH + username
        if not os.path.exists(USER_PATH):
            os.mkdir(USER_PATH)

        if ids:  # ids是checkbox如果激活会传回来为ids
            get_total_amount = []
            store_data = []
            company = ""
            # 所有价格的综合

            for id in ids:
                # 解析每张发票并传送到服务器
                each = invoice_db.each_invoice(int(id))
                # 取所有发票的价格
                get_total_amount.append(each.amount)

                # 把文件临时村在服务器
                # convert_date = str(each.date)
                convert_date = datetime.strftime(each.date, "%Y-%m-%d")
                file_name = f"{convert_date}({each.id}-¥{each.amount}).pdf"
                file_join = os.path.join(USER_PATH, file_name)
                with open(file_join, "wb") as file:
                    encoded_string = base64.b64decode(each.pdf)
                    file.write(encoded_string)

                company = each.company
                store_data.append(each)
                # 如果下载成功把download改为True
                invoice_db.download(invoice_id=each.id)

            # excel
            excel(username=username, company=company, data=store_data)

            # 建立ZIP名字
            zip_name = f"{year}年(¥{sum(get_total_amount):0.2f}).zip"
            zip_join = os.path.join(USER_PATH, zip_name)
            # 取所有PDF并存在ZIP里
            with ZipFile(zip_join, "w") as zip_file:
                for parent, dirnames, filenames in os.walk(USER_PATH):
                    for pdf in filenames:
                        if pdf.lower().endswith(".pdf") or pdf.lower().endswith(
                            ".xlsx"
                        ):
                            pdf_path = os.path.join(parent, pdf)
                            zip_file.write(
                                pdf_path, arcname=os.path.relpath(pdf_path, USER_PATH)
                            )
            return FileResponse(path=zip_join, filename=zip_name)

        # ---------- 上传区 ----------
        _invoice_scan = InvoiceScan()
        current_user = user_db.user_info(username)
        for file in files:
            with open(file.filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                err_msg = _invoice_scan.pdf_file(
                    user_id=current_user.id, file=file.filename
                )
                os.remove(file.filename)
                if err_msg:
                    _error.append(err_msg)
            try:
                year: str = _invoice_scan.date.year
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
