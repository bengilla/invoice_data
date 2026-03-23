"""发票系统主页"""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from routes.local_invoice import local_invoice_routes

app = FastAPI(title="发票管理系统", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="images"), name="images")


@app.get("/")
async def root():
    return RedirectResponse(url="/local", status_code=302)


@app.get("/local")
async def local_page():
    return FileResponse("invoice_system.html")


app.include_router(local_invoice_routes)
