from fastapi import FastAPI
from .router.user import router as user_router
from .router.downloader import router as downloader_router

app = FastAPI()

app.include_router(user_router, prefix="/api/user")
app.include_router(downloader_router, prefix="/api/downloader")


@app.get("/")
def main_route():
    return "running"
