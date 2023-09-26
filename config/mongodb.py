"""MongoDB function"""
from pymongo import MongoClient
from config.settings import settings
from typing import Any


class MongoDB:
    """MongoDB"""

    def __init__(self) -> None:
        # MongoDB connect to Local or Online Server-------------------------------
        self.client = MongoClient(settings.DB_URL, serverSelectionTimeoutMS=3000)

        # Collection info
        self.invoice = self.client["INVOICE-DATA"]

    def status(self) -> dict[str, Any]:
        """DB status"""
        return self.client.server_info()

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def list_collections(self) -> list[str]:
        if not self.invoice.list_collection_names():
            return []
        return sorted(self.invoice.list_collection_names())
