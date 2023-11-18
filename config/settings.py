"""设置区"""
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Settings:
    """所有设置"""

    TITLE = "发票管理"
    VERSION = "0.1"
    DESCRIPTION = "中国发票管理系统"

    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    PORT: int = os.getenv("PORT")

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")

    DB_URL: str = os.getenv("DB_URL")
    MySQL: str = f"mysql+mysqlconnector://root:{DB_PASSWORD}@localhost:3306/invoice_db"
    # LOCATION = "/Users/bengilla/Documents/coding/invoice_data/"
    LOCATION = "/"
