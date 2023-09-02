from fastapi import FastAPI
from .router.user import router as user_router

app = FastAPI()

app.include_router(user_router, prefix="/api/user")


@app.get("/")
async def main_route():
    return {"message": "Hey, It is me Goku"}
