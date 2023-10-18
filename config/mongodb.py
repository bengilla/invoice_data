"""MongoDB function"""
from typing import Any

from pymongo import MongoClient

from config.settings import Settings

_settings = Settings()


class MongoDB:
    """MongoDB"""

    def __init__(self) -> None:
        # MongoDB connect to Local or Online Server-------------------------------
        # self.client = MongoClient(
        #     f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@invoice.8bomvyv.mongodb.net/"
        # )
        self.client = MongoClient("mongodb://localhost:27017")

        # Collection info
        self.invoice = self.client["INVOICE-DATA"]

    def user_data(self, username: str):
        """to user collection"""
        user = self.client["INVOICE-USER"]
        return user[username]

    def user_collection(self) -> list[str]:
        """get user collections name"""
        user_collection = self.client["INVOICE-USER"]
        user_list = user_collection.list_collection_names()
        return user_list

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def collections(self) -> list[str]:
        """get collection list"""
        month_list = self.invoice.list_collection_names()
        return sorted(month_list, key=int)
