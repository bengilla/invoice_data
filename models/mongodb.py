from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from config.settings import settings


class MongoDB:
    def __init__(self) -> None:
        # Local Testing MongoDB-------------------------------
        # self.client = MongoClient(settings.DB_LOCAL, serverSelectionTimeoutMS=3000)
        self.client = MongoClient(settings.DB_URL, serverSelectionTimeoutMS=3000)

        # member info
        self.bill = self.client["BILL"]

    # db status
    def status(self):
        """DB status"""
        try:
            server_info = self.client.server_info()
            if server_info["ok"] == 1.0:
                return True
        except ServerSelectionTimeoutError:
            return False

    def send_data(self, month):
        return self.bill[str(month)]

    def list_collections(self):
        return self.bill.list_collection_names()
