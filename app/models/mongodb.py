"""MongoDB function"""
from pymongo import MongoClient
from config.settings import settings


class CodeDB:
    def __init__(self) -> None:
        self.code_client = MongoClient(settings.CODE_URL)
        self.code = self.code_client["CODE"]

    def verify_code(self) -> list[str]:
        return self.code["temp_code"]


class MongoDB:
    """MongoDB"""

    def __init__(self, username) -> None:
        # MongoDB connect to Local or Online Server-------------------------------
        self.client = MongoClient(settings.DB_URL, serverSelectionTimeoutMS=3000)

        # Collection info
        self.invoice_user = self.client["INVOICE_USER_INFO"]
        self.invoice = self.client[username.lower()]

    def status(self) -> bool:
        """DB status"""
        try:
            self.client.server_info()
            return True
        except:
            return False

    def user(self):
        return self.invoice_user["USER-data"]

    # def list_user(self) -> list[str]:
    #     """return sort list collection"""
    #     return self.invoice_user.list_collection_names()

    def send_data(self, month: str):
        """to collection"""
        return self.invoice[str(month)]

    def list_collections(self) -> list[str]:
        return sorted(map(int, self.invoice.list_collection_names()))
