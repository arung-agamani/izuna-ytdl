from fastapi import FastAPI
from .router.user import router as userRouter

app = FastAPI()

app.include_router(userRouter, prefix="/api/user")


@app.get("/")
async def main_route():
    return {"message": "Hey, It is me Goku"}
