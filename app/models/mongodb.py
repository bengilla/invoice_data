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
        self.code = self.client["CODE"]
        self.invoice = self.client["INVOICE-DATA"]
        self.invoice_user = self.client["INVOICE-USER_INFO"]

    def status(self) -> bool:
        """DB status"""
        server_info = self.client.server_info()
        if server_info["ok"] == 1.0:
            return True
        return False

    def verify_code(self) -> list:
        return self.code["temp_code"]

    def user(self, username: str):
        return self.invoice_user[username]

    def list_user_collections(self) -> list[str]:
        """return sort list collection"""
        list_collection = [x for x in self.invoice_user.list_collection_names()]
        return list_collection

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def list_collections(self) -> list[str]:
        """return sort list collection"""
        list_collection = [int(x) for x in self.invoice.list_collection_names()]
        list_collection.sort(key=int)
        return list_collection
