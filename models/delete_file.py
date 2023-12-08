"""删除文件功能区"""
import os


def delete_file(username: str) -> None:
    """删除所有PDF和ZIP文件"""
    PATH = os.getcwd() + "/user_file/"
    USER_PATH = PATH + username
    for parent, dirnames, filenames in os.walk(USER_PATH):
        for fn in filenames:
            if (
                fn.lower().endswith(".pdf")
                or fn.lower().endswith(".zip")
                or fn.lower().endswith(".xlsx")
            ):
                os.remove(os.path.join(parent, fn))
