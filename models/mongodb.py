from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from config.settings import settings


class MongoDB:
    def __init__(self) -> None:
        # Local Testing MongoDB-------------------------------
        self.client = MongoClient(settings.DB_LOCAL, serverSelectionTimeoutMS=3000)
        # self.client = MongoClient(settings.DB_URL, serverSelectionTimeoutMS=3000)

        # collection info
        self.invoice = self.client["INVOICE"]

    # db status
    def status(self) -> bool:
        """DB status"""
        try:
            server_info = self.client.server_info()
            if server_info["ok"] == 1.0:
                return True
        except ServerSelectionTimeoutError:
            return False

    # collection
    def send_data(self, month: str):
        return self.invoice[str(month)]

    # list of collection
    def list_collections(self) -> list:
        """return sort list collection"""
        collection = self.invoice.list_collection_names()
        list_collection = [x for x in collection]
        return sorted(list_collection)
