"""发票处理功能区"""
from typing import Any

import re
import base64
import pendulum
import pdfplumber
from pymongo.errors import DuplicateKeyError

from db.mongodb import MongoDB


class Invoice:
    """计算所有发票讯息"""

    def __init__(self) -> None:
        self.date = None
        self._db_mongo = MongoDB()

    def pdf_file(self, username: str, file: Any):
        """计算所有发票讯息并输出db_data"""
        # file show up is xxxx.pdf
        try:
            # 把PDF发票转换成数据
            with pdfplumber.open(file) as pdf:
                invoice_content: list = []
                for item, _ in enumerate(pdf.pages):
                    page = pdf.pages[item]
                    page_content: list = page.extract_text().split("\n")[:-1]
                    invoice_content.append(page_content)

            # print(invoice_content[0])

            # 数据模型 (date, number, amount, company, download)
            db_data = {}

            # 计算数据区
            store_company = []
            for info in invoice_content[0]:
                if "个人" in info:
                    store_company.append("个人")
                else:
                    if "公司" in info:
                        get_company_name: str = re.split(" |：|:", info)
                        # print(get_company_name)
                        for c_n in get_company_name:
                            if "公司" in c_n:
                                store_company.append(c_n)
                        if "个人" in store_company:
                            db_data["company"] = "个人"
                        db_data["company"] = store_company[0]
                        # print(store_company[0])
                if "开票日期" in info:
                    get_date: str = re.findall(r"\d*", info)
                    date_convert = "".join(get_date)
                    self.date = pendulum.from_format(date_convert, "YYYYMMDD")
                    db_data["date"] = self.date
                if "发票号码" in info:
                    get_number: str = re.findall(r"\d*", info)
                    # print("".join(get_number)[-10:])
                    db_data["_id"] = int("".join(get_number)[-10:])
                if "小写" in info:
                    get_amount: str = re.findall(r"\d+\.?\d*", info)
                    # print(get_amount[-1])
                    db_data["amount"] = float(get_amount[-1])

            # 把PDF转换成base64
            with open(file, "rb") as pdf:
                encoded = base64.b64encode(pdf.read())
                db_data["pdf"] = encoded

            # 下载初始化为False
            db_data["download"] = False

            # 存储在数据库
            db_upload = self._db_mongo.invoice_data(username).insert_one(db_data)
            if db_upload:
                return f"{db_data['_id']} 上传成功"
            return f"{db_data['_id']} 上传失败"
        except DuplicateKeyError:
            # 如果文件重复
            return f"重复文件, 发票代码: {db_data['_id']}"
        except:
            return "文件异常, 请重新上传发票(PDF)"
