import os
import fnmatch

from config.settings import Settings

_settings = Settings()


def delete_all_file() -> None:
    """Delete pdf and zip function"""
    for file in os.listdir(_settings.LOCATION):
        if fnmatch.fnmatch(file, "*.zip") or fnmatch.fnmatch(file, "*.pdf"):
            os.remove(file)
