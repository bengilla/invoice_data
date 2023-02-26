import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    TITLE = "Bill Calculate"
    VERSION = "0.1"
    DESCRIPTION = ""

    DB_LOCAL = os.getenv("DB_LOCAL")
    DB_URL = os.getenv("DB_URL")


settings = Settings()
