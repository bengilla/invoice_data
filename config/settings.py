"""Settings section"""
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Settings:
    """Config all settings"""

    TITLE = "Invoice Calculate"
    VERSION = "0.1"
    DESCRIPTION = "China invoice calculation system"

    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    PORT: int = os.getenv("PORT")


settings = Settings()
