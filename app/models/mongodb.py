"""MongoDB function"""
from pymongo import MongoClient
from config.settings import settings


class MongoDB:
    """MongoDB"""

    def __init__(self) -> None:
        # MongoDB connect to Local or Online Server-------------------------------
        self.client = MongoClient(settings.DB_URL, serverSelectionTimeoutMS=3000)

        # Collection info
        self.invoice = self.client["INVOICE-DATA"]

    def status(self) -> bool:
        """DB status"""
        return self.client.server_info()

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def list_collections(self) -> list[str]:
        return sorted(map(int, self.invoice.list_collection_names()))
