"""Settings section"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Config all settings"""

    TITLE = "Invoice Calculate"
    VERSION = "0.1"
    DESCRIPTION = "China invoice calculation system"

    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")

    DB_LOCAL = os.getenv("DB_LOCAL")
    DB_URL = os.getenv("DB_URL")

    CODE_URL = os.getenv("CODE_URL")


settings = Settings()
