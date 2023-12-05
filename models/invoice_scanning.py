"""发票处理功能区"""
from typing import Any

import re
import base64
import pdfplumber
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from db.db import Invoices


class InvoiceScan:
    """计算所有发票讯息"""

    def __init__(self) -> None:
        self.date = None

    def pdf_file(self, user_id: int, file: Any):
        """计算所有发票讯息并输出db_data"""
        _db_invoice = Invoices()
        # 文件名字为 xxxx.pdf
        try:
            # 把PDF发票转换成数据
            with pdfplumber.open(file) as pdf:
                invoice_content: list = []
                for item, _ in enumerate(pdf.pages):
                    page = pdf.pages[item]
                    page_content: list = page.extract_text().split("\n")[:-1]
                    invoice_content.append(page_content)

            # print(invoice_content[0])

            # 数据模型 (date, number, amount, company, download, user_id)
            db_data = {}

            # 用户ID
            db_data["user_id"] = user_id

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
                    self.date = datetime.strptime(date_convert, "%Y%m%d")
                    db_data["date"] = self.date
                if "发票号码" in info:
                    get_number: str = re.findall(r"\d*", info)
                    # print("".join(get_number)[-10:])
                    db_data["id"] = int("".join(get_number)[-10:])
                if "小写" in info:
                    get_amount: str = re.findall(r"\d+\.?\d*", info)
                    # print(get_amount[-1])
                    db_data["amount"] = float(get_amount[-1])

            # 把PDF转换成base64
            with open(file, "rb") as pdf:
                encoded = base64.b64encode(pdf.read())
                db_data["pdf"] = encoded

            # print(db_data)

            # 上传数据至数据库
            _db_invoice.store_invoice(**db_data)
            # 存储在数据库
            return f"{db_data['id']} 上传成功"
        except IntegrityError:
            return f"文件重复，发票号码: {db_data['id']}"
        except:
            return f"文件异常, 请重新上传发票(PDF)"
