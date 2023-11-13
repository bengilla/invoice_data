"""删除文件功能区"""
import os
import fnmatch
from config.settings import Settings

_settings = Settings()


def delete_all_file() -> None:
    """删除所有PDF和ZIP文件"""
    for file in os.listdir(_settings.LOCATION):
        if fnmatch.fnmatch(file, "*.zip") or fnmatch.fnmatch(file, "*.pdf"):
            os.remove(file)
