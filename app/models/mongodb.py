"""MongoDB function"""
from pymongo import MongoClient
from config.settings import settings


class MongoDB:
    """MongoDB"""

    def __init__(self) -> None:
        # MongoDB connect to Local or Online Server-------------------------------
        # self.client = MongoClient(settings.DB_LOCAL, serverSelectionTimeoutMS=3000)
        self.client = MongoClient(settings.DB_URL, serverSelectionTimeoutMS=3000)

        # Collection info
        self.invoice = self.client["INVOICE"]

    def status(self) -> bool:
        """DB status"""
        server_info = self.client.server_info()
        if server_info["ok"] == 1.0:
            return True
        return False

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def list_collections(self) -> list[str]:
        """return sort list collection"""
        list_collection = list(self.invoice.list_collection_names())
        return sorted(list_collection)
