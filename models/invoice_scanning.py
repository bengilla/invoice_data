"""invoice work section"""
from typing import Any

import base64
import pendulum
import pdfplumber
from pymongo.errors import DuplicateKeyError

from config.mongodb import MongoDB
from config.company_data import company_data

_db = MongoDB()


class Invoice:
    """All function about invoice calculate"""

    def __init__(self) -> None:
        self.date = None

    @staticmethod
    def get_data(content) -> dict[str, str | int | float]:
        """take piece by piece convert to final data (dict)"""
        # this data when register and save to database as company name
        # print(content)

        # store data models
        store_data_model = {
            "date": [],
            "number": [],
            "amount": [],
            "company": "",
        }

        # check company name from the company_data and the invoice company title
        for company_name in company_data:
            for invoice_company_name in content[0]:
                if company_name in invoice_company_name:
                    store_data_model["company"] = company_name

        # get date, number and amount from invoice
        for info in content[0]:
            if "开票日期" in info:
                for date_invoice in info:
                    if date_invoice.isdigit():
                        store_data_model["date"].append(date_invoice)
            if "发票号码" in info:
                for number_invoice in info:
                    if number_invoice.isdigit():
                        store_data_model["number"].append(number_invoice)
            if "¥" in info or "￥" in info:
                store_data_model["amount"].append(info)

        # get amount need to get float after currency symbol + 1 empty space
        currency_symbol = store_data_model["amount"][1]
        currency_symbol_index = currency_symbol.find("¥") or currency_symbol.find("￥")

        # print(f"This is Store Data Model{store_data_model}")

        result_data = {
            "date_output": "".join(store_data_model["date"]),
            "num_output": int("".join(store_data_model["number"][-8:])),
            "amount_output": float(
                store_data_model["amount"][1][currency_symbol_index + 1 :]
            ),
            "company": "".join(store_data_model["company"]),
            "download": False,
        }
        # print(f"This is result_data{result_data}")

        return result_data

    def pdf_file(self, file: Any):
        """final output all data to db"""
        try:
            # take all data from PDF
            with pdfplumber.open(file) as pdf:
                content = []
                for item, _ in enumerate(pdf.pages):
                    page = pdf.pages[item]
                    page_content = page.extract_text().split("\n")[:-1]
                    content.append(page_content)

            # calculate all data to format
            result_final_data = self.get_data(content)

            # date section, year and month are from invoice data
            self.date = pendulum.from_format(
                result_final_data["date_output"], "YYYYMMDD"
            )

            # encode pdf file and store to db
            with open(file, "rb") as pdf:
                encoded = base64.b64encode(pdf.read())

            db_data = {
                "_id": result_final_data["num_output"],
                "date": self.date.to_date_string(),
                "amount": f"{result_final_data['amount_output']:0.2f}",
                "pdf": encoded,
                "company": result_final_data["company"],
                "download": result_final_data["download"],
            }

            # store to db
            db_upload = _db.send_data(str(self.date.month)).insert_one(db_data)
            if db_upload:
                return f"{result_final_data['num_output']} 上传成功"
            return f"{result_final_data['num_output']} 上传失败"
        except DuplicateKeyError:
            # when duplicate file
            return f"重复文件, 发票代码: {result_final_data['num_output']}"
        except Exception as err:
            # other error
            print(err)
            return "文件异常, 请重新上传发票(PDF)"
