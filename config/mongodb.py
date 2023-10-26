"""所有跟数据库有关的"""
from datetime import date

from pymongo import MongoClient

from config.settings import Settings

_settings = Settings()


class MongoDB:
    """数据库"""

    def __init__(self) -> None:
        """主区"""

        self.client = MongoClient("mongodb://localhost:27017")
        # self.client = MongoClient(
        #     f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@invoice.8bomvyv.mongodb.net/"
        # )
        self.code_client = MongoClient(
            f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@bengilla.4ny2nkw.mongodb.net/?retryWrites=true&w=majority"
        )

    """发票区"""

    def invoice_data(self, username: str):
        invoice = self.client["INVOICE-DATA"]
        return invoice[username]

    def year_n_month(self, username: str):
        result = {"year": [], "month": []}
        invoice_data = self.invoice_data(username).find({})
        for each_invoice in invoice_data:
            d = date.fromisoformat(each_invoice["date"])
            if d.month not in result["month"]:
                result["month"].append(d.month)
            if d.year not in result["year"]:
                result["year"].append(d.year)
        return result

    """确认码"""

    def verify_code(self) -> list:
        code = self.code_client["CODE"]
        code_find = code["temp_code"].find({})
        code_list = [c["code"] for c in code_find]
        return code_list
