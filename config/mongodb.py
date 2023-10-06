"""MongoDB function"""
from typing import Any

from pymongo import MongoClient
from config.settings import settings


class MongoDB:
    """MongoDB"""

    def __init__(self) -> None:
        # MongoDB connect to Local or Online Server-------------------------------
        self.client = MongoClient(settings.DB_URL)

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
        return sorted(self.invoice.list_collection_names())
