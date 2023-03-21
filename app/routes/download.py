"""Download Section"""
from fastapi import APIRouter
from fastapi.responses import FileResponse

download_routes = APIRouter()


@download_routes.get("/download/{file}")
async def download(file: str):
    """Download file section"""
    return FileResponse(path=file, filename=file)
