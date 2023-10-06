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

    @staticmethod
    def get_data(content) -> dict[str, str, float, str, bool]:
        """take piece by piece convert to final data (dict)"""
        # this data when register and save to database as company name
        # print(content)

        # store data models
        store_data_model = {
            "date": [],
            "number": [],
            "amount": [],
            "company": [],
        }

        # get date, number and amount from invoice
        for info in content:
            if "个人" in info:
                store_data_model["company"].append("个人")
            else:
                if "公司" in info:
                    get_company_name: str = re.split(" |：|:", info)
                    for c_n in get_company_name:
                        if "公司" in c_n:
                            store_data_model["company"].append(c_n)
            if "开票日期" in info:
                get_date: str = re.findall(r"\d*", info)
                store_data_model["date"].append("".join(get_date))
            if "发票号码" in info:
                get_number: str = re.findall(r"\d*", info)
                store_data_model["number"].append("".join(get_number))
            if "小写" in info:
                get_amount: str = re.findall(r"\d+\.?\d*", info)
                store_data_model["amount"].append(get_amount[0])

        # print(f"This is Store Data Model{store_data_model}")

        result_data = {
            "date_output": store_data_model["date"][0],
            "num_output": store_data_model["number"][0],
            "amount_output": float(store_data_model["amount"][0]),
            "company": store_data_model["company"][0],
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
            result_final_data = self.get_data(content[0])

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
