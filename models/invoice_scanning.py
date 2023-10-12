"""invoice work section"""
from typing import Any

import re
import base64
import pendulum
import pdfplumber
from pymongo.errors import DuplicateKeyError

from config.mongodb import MongoDB

_db = MongoDB()


class Invoice:
    """All function about invoice calculate"""

    def __init__(self) -> None:
        self.date = None

    def pdf_file(self, file: Any):
        """final output all data to db"""
        # file show up is xxxx.pdf
        try:
            # turn pdf content to text
            with pdfplumber.open(file) as pdf:
                invoice_content: list = []
                for item, _ in enumerate(pdf.pages):
                    page = pdf.pages[item]
                    page_content: list = page.extract_text().split("\n")[:-1]
                    invoice_content.append(page_content)

            # print(invoice_content[0])

            # store data models (date, number, amount, company, download)
            db_data = {}

            # pick data from content
            store_company = []
            for info in invoice_content[0]:
                if "个人" in info:
                    store_company.append("个人")
                else:
                    if "公司" in info:
                        get_company_name: str = re.split(" |：|:", info)
                        for c_n in get_company_name:
                            if "公司" in c_n:
                                store_company.append(c_n)
                        if "个人" in store_company:
                            db_data["company"] = "个人"
                        db_data["company"] = store_company[0]
                if "开票日期" in info:
                    get_date: str = re.findall(r"\d*", info)
                    date_convert = "".join(get_date)
                    self.date = pendulum.from_format(
                        date_convert, "YYYYMMDD"
                    )  # convert string to date
                    db_data["date"] = self.date.to_date_string()
                if "发票号码" in info:
                    get_number: str = re.findall(r"\d*", info)
                    db_data["_id"] = "".join(get_number)
                if "小写" in info:
                    get_amount: str = re.findall(r"\d+\.?\d*", info)
                    print(get_amount)
                    db_data["amount"] = get_amount[-1]

            # encode pdf file and store to db
            with open(file, "rb") as pdf:
                encoded = base64.b64encode(pdf.read())
                db_data["pdf"] = encoded

            # insert download False
            db_data["download"] = False

            # print(db_data)

            # store to db
            db_upload = _db.send_data(str(self.date.month)).insert_one(db_data)
            if db_upload:
                return f"{db_data['_id']} 上传成功"
            return f"{db_data['_id']} 上传失败"
        except DuplicateKeyError:
            # when duplicate file
            return f"重复文件, 发票代码: {db_data['_id']}"
        except:
            return "文件异常, 请重新上传发票(PDF)"
