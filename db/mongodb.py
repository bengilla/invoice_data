"""所有跟数据库有关的"""
from typing import List

from pymongo import MongoClient

from config.settings import Settings

_settings = Settings


class MongoDB:
    """数据库"""

    def __init__(self) -> None:
        """主区"""
        # self.client = MongoClient("mongodb://localhost:27017")
        self.client = MongoClient(
            f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@invoice.8bomvyv.mongodb.net/"
        )

    """确认码"""

    def verify_code(self) -> List[str]:
        self.code_client = MongoClient(
            f"mongodb+srv://bengilla:{_settings.DB_PASSWORD}@bengilla.4ny2nkw.mongodb.net/?retryWrites=true&w=majority"
        )
        code = self.code_client["CODE"]
        code_find = code["temp_code"].find({})
        code_list = [c["code"] for c in code_find]
        return code_list
