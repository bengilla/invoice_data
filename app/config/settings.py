"""Settings section"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Config all settings"""

    TITLE = "Invoice Calculate"
    VERSION = "0.1"
    DESCRIPTION = ""

    DB_LOCAL = os.getenv("DB_LOCAL")
    DB_URL = os.getenv("DB_URL")

    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")


settings = Settings()
