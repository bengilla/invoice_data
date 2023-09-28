"""invoice work section"""
import base64
import pendulum
import pdfplumber
from typing import Any
from pymongo.errors import DuplicateKeyError

from config.mongodb import MongoDB

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

        # store data models
        store_data_model = {
            "date": [],
            "number": [],
            "amount": [],
            "company": "",
        }
        print(f"This is store_data {store_data_model}")

        # get company name
        for i in company_data:
            for company_name in content[0]:
                if i in company_name:
                    store_data_model["company"] = i

        # work below (get company name)
        title_data = {
            "date": "开票日期",
            "number": "发票号码",
        }
        print(f"This is title_data {title_data}")

        # get date, code and number
        for key, value in title_data.items():
            for item in content[0]:
                if value in item:
                    for i in item:
                        if i.isdigit():
                            store_data_model[key].append(i)
                if "¥" in item or "￥" in item:
                    store_data_model["amount"].append(item)

        # get amount
        for i in store_data_model["amount"][1]:
            if i in ("¥", "￥"):
                num = store_data_model["amount"][1].index(i)

        result_data = {
            "date_output": "".join(store_data_model["date"]),
            "num_output": int("".join(store_data_model["number"][-8:])),
            "amount_output": float(store_data_model["amount"][1][num + 1 :]),
            "company": "".join(store_data_model["company"]),
        }
        print(f"This is result_data{result_data}")

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
            print(f"This is result_final_data {result_final_data}")

            # date section, year and month are from invoice data
            self.date = pendulum.from_format(
                result_final_data["date_output"], "YYYYMMDD"
            )
            print(f"This is self.date {self.date.year}")

            # encode pdf file and store to db
            with open(file, "rb") as pdf:
                encoded = base64.b64encode(pdf.read())

            db_data = {
                "_id": result_final_data["num_output"],
                "date": self.date.to_date_string(),
                "amount": f"{result_final_data['amount_output']:0.2f}",
                "pdf": encoded,
                "company": result_final_data["company"],
                "download": False,
            }
            # testing print out the db_data
            print(f"This is db_data {db_data}")

            # store to db
            db_upload = _db.send_data(str(self.date.month)).insert_one(db_data)
            if db_upload:
                return f"{result_final_data['num_output']} 上传成功"
            return f"{result_final_data['num_output']} 上传失败"
        except DuplicateKeyError:
            # when duplicate file
            return f"重复文件, 发票代码: {result_final_data['num_output']}"
        except Exception as e:
            # other error
            print(e)
            return "文件异常, 请重新上传发票(PDF)"
