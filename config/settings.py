"""Settings section"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Config all settings"""

    TITLE = "Invoice Calculate"
    VERSION = "0.1"
    DESCRIPTION = "China invoice calculation system"

    DB_URL = os.getenv("DB_URL")


settings = Settings()
