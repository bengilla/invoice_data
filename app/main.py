"""Invoice Calculate"""
import os
import fnmatch
import codecs
import shutil
from datetime import datetime
from passlib.context import CryptContext

from zipfile import ZipFile

from fastapi import FastAPI, Request, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from models.invoice_scanning import Invoice
from models.mongodb import MongoDB, CodeDB
from routes.download import download_routes
from routes.check import check_routes


app = FastAPI(title=settings.TITLE)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
_db = MongoDB()
_code_db = CodeDB()
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
    response = templates.TemplateResponse("index.html", {"request": request})
    return response


@app.post("/")
async def index_post(
    request: Request, email: str = Form(...), password: str = Form(...)
):
    # if user exists login and jump to month page and if user not exists create user
    user_data = _db.user().find({})

    for user in user_data:
        if email == user["email"]:
            if _pwd_context.verify(password, user["password"]):
                count = list(_db.list_collections())
                if len(count) == 0:
                    num = "0"
                else:
                    num = count[0]
                return RedirectResponse(
                    request.url_for("main", num=num), status_code=302
                )
    return {"讯息": "邮箱和密码错误，请返回再次尝试"}


@app.get("/register", response_class=HTMLResponse)
async def index(request: Request):
    """Upload pdf file when db is empty"""
    response = templates.TemplateResponse("register.html", {"request": request})
    return response


@app.post("/register")
async def index_post(
    email: str = Form(...),
    password: str = Form(...),
    code: str = Form(...),
):
    def get_code() -> list:
        code_list = []
        for i in _code_db.verify_code().find({}):
            code_list.append(i["code"])
        return code_list

    verify_code = get_code()

    user_data = _db.user().find({})
    user_list = [i["email"] for i in user_data]

    encode_password = _pwd_context.hash(password)

    # if code match with verify code at database
    if code in verify_code:
        if email not in user_list:
            # create new user
            new_user = {
                "email": email,
                "password": encode_password,
                "register_date": datetime.now(),
                "company": [],
            }
            result = _db.user().insert_one(new_user)

            # after add user and delete verify code from database
            get_code = _code_db.verify_code().find_one({"code": code})
            _code_db.verify_code().delete_one({"_id": get_code["_id"]})

            return {
                "讯息": "用户已成功建立",
                "用户ID": str(result.inserted_id),
            }
        else:
            return {"讯息": "邮箱已存在，请使用另一个邮箱"}
    else:
        return {"讯息": "确认码错误，请向管理员质询"}


@app.get("/month/{num}", response_class=HTMLResponse)
async def main(*, request: Request, num: str):
    """When previous pdf file is in db"""
    # --------------------------------------------------
    # username = ""
    # password = ""
    # Get the user data directly in the find_one_and_update query
    # user_data = _db.user(username).find_one_and_update(
    #     {"name": username},
    #     {
    #         "$push": {"company": "南京画文文化有限公司"},
    #         "$currentDate": {"lastModified": True},
    #     },
    # )
    # --------------------------------------------------
    delete_all_file()  # delete all zip and pdf file

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

                # if download success turn downlaod icon to True
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
