"""invoice work section"""
import base64
import pendulum
import pdfplumber
from typing import Any
from pymongo.errors import DuplicateKeyError

from .mongodb import MongoDB

_db = MongoDB()


class Invoice:
    """All function about invoice calculate"""

    def __init__(self) -> None:
        self.date = None

    def get_data(self, content) -> dict[str, str | int | float]:
        """take piece by piece convert to final data (dict)"""
        # this data when register and save to database as company name
        company_data = [
            "北京忠合天歌文化产业有限公司",
            "北京安和嘉音光电技术有限公司",
            "北京画文文化有限公司",
            "南京画文文化有限公司",
            "个人",
        ]

        # final store data
        store_data = {
            "date": [],
            "code": [],
            "number": [],
            "amount": [],
            "company": "",
        }

        # get company name
        for i in company_data:
            for company_name in content[0]:
                if i in company_name:
                    store_data["company"] = i

        # work below (get company name)
        title_data = {
            "date": "开票日期",
            "code": "发票代码",
            "number": "发票号码",
        }
        # get date, code and number
        for key, value in title_data.items():
            for item in content[0]:
                if value in item:
                    for i in item:
                        if i.isdigit():
                            store_data[key].append(i)
                if "¥" in item or "￥" in item:
                    store_data["amount"].append(item)

        # get amount
        for i in store_data["amount"][1]:
            if i in ("¥", "￥"):
                num = store_data["amount"][1].index(i)

        # print(store_data)

        result_data = {
            "date_output": "".join(store_data["date"]),
            "code_output": int("".join(store_data["code"])),
            "num_output": int("".join(store_data["number"])),
            "amount_output": float(store_data["amount"][1][num + 1 :]),
            "company": "".join(store_data["company"]),
        }

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
                print(content)

            # calculate all data to format
            result_data = self.get_data(content)
            # print(result_data)

            # date section, year and month are from invoice data
            self.date = pendulum.from_format(result_data["date_output"], "YYYYMMDD")
            print(self.date.year)

            # encode pdf file and store to db
            with open(file, "rb") as pdf:
                encoded = base64.b64encode(pdf.read())

            db_data = {
                "_id": result_data["num_output"],
                "date": self.date.to_date_string(),
                "code": result_data["code_output"],
                "amount": f"{result_data['amount_output']:0.2f}",
                "pdf": encoded,
                "company": result_data["company"],
                "download": False,
            }
            # print(db_data)

            # store to db
            db_upload = _db.send_data(str(self.date.month)).insert_one(db_data)
            if db_upload:
                return f"{result_data['num_output']} 上传成功"
            return f"{result_data['num_output']} 上传失败"
        except DuplicateKeyError:
            # when duplicate file
            return f"重复文件, 发票代码: {result_data['num_output']}"
        except Exception as error:
            # other error
            print(error)
            # return "文件异常, 请重新上传发票(PDF)"
