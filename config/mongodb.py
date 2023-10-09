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

    def status(self) -> dict[str, Any]:
        """DB status"""
        return self.client.server_info()

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def list_collections(self) -> list[str]:
        """get collection list"""
        if not self.invoice.list_collection_names():
            return []
        re_arrange_number = self.invoice.list_collection_names()
        return sorted(re_arrange_number, key=int)
