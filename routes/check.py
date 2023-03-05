"""Check File on Server Section"""

import os
import fnmatch
from fastapi import APIRouter

check_routes = APIRouter()


@check_routes.get("/check/")
async def check():
    """Check all zip and pdf file"""

    def count_size(size):
        if size < 1000:
            return f"{size} bytes"
        if 100000 > size >= 1000:
            return f"{round(size / 1000, 2)} KB"
        return f"{round(size / 1000000, 2)} MB"

    def file_info(file, size):
        data = {"file_name": file, "file_size": size}
        return data

    file_list = []
    for _root, _dir, files in os.walk("/"):
        for name in files:
            if fnmatch.fnmatch(name, "*.zip"):
                get_size = os.path.getsize(name)
                output_data = file_info(name, count_size(get_size))
                file_list.append(output_data)
            if fnmatch.fnmatch(name, "*.pdf"):
                get_size = os.path.getsize(name)
                output_data = file_info(name, count_size(get_size))
                file_list.append(output_data)

    return {"message": file_list}
