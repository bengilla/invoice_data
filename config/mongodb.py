"""所有跟数据库有关的"""
import pendulum

from pymongo import MongoClient

from config.settings import Settings

_settings = Settings()


class MongoDB:
    """数据库"""

    def __init__(self) -> None:
        """Main Section"""

        self.client = MongoClient("mongodb://localhost:27017")
        # self.client = MongoClient(
        #     f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@invoice.8bomvyv.mongodb.net/"
        # )
        self.code_client = MongoClient(
            f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@bengilla.4ny2nkw.mongodb.net/?retryWrites=true&w=majority"
        )

    """ User Section"""

    def user_data(self, username: str):
        """to user collection"""
        user = self.client["INVOICE-USER"]
        return user[username]

    def user_collection(self) -> list[str]:
        """get user collections name"""
        user_collection = self.client["INVOICE-USER"]
        user_list = user_collection.list_collection_names()
        return user_list

    """Invoice Section"""

    def invoice_data(self, username: str):
        """to collection"""
        invoice = self.client["INVOICE-DATA"]
        return invoice[username]

    # def invoice_collections(self) -> list[str]:
    #     """get collection list"""
    #     invoice = self.client["INVOICE-DATA"]
    #     month_list = invoice.list_collection_names()
    #     return sorted(month_list, key=int)

    def all_invoice_data(self, username: str) -> list[dict]:
        invoice_data = self.invoice_data(username).find({})
        return invoice_data

    def get_month_list(self, username: str) -> list[int]:
        month_list: list[int] = []
        invoice_data = self.invoice_data(username).find({})
        for each_invoice in invoice_data:
            date: pendulum = pendulum.from_format(each_invoice["date"], "YYYY-MM-DD")
            if date.month not in month_list:
                month_list.append(date.month)
        return month_list

    """确认码"""

    def verify_code(self) -> list:
        code = self.code_client["CODE"]
        code_find = code["temp_code"].find({})
        code_list = [c["code"] for c in code_find]
        return code_list
