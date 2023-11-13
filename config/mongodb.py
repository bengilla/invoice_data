"""MongoDB function"""
from typing import Any

from pymongo import MongoClient

from config.settings import Settings

_settings = Settings()


class MongoDB:
    """MongoDB"""

    def __init__(self) -> None:
        # MongoDB connect to Local or Online Server
        # self.client = MongoClient("mongodb://localhost:27017")
        self.client = MongoClient(
            f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@invoice.8bomvyv.mongodb.net/"
        )
        self.code_client = MongoClient(
            f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@bengilla.4ny2nkw.mongodb.net/?retryWrites=true&w=majority"
        )

    def user_data(self, username: str):
        """to user collection"""
        user = self.client["INVOICE-USER"]
        return user[username]

    def user_collection(self) -> list[str]:
        """get user collections name"""
        user_collection = self.client["INVOICE-USER"]
        user_list = user_collection.list_collection_names()
        return user_list

    def invoice_data(self, month: str):
        """to collection"""
        invoice = self.client["INVOICE-DATA"]
        return invoice[str(month)]

    def invoice_collections(self) -> list[str]:
        """get collection list"""
        invoice = self.client["INVOICE-DATA"]
        month_list = invoice.list_collection_names()
        return sorted(month_list, key=int)

    def verify_code(self) -> list:
        code = self.code_client["CODE"]
        code_find = code["temp_code"].find({})
        code_list = [c["code"] for c in code_find]
        return code_list
