from dotenv import load_dotenv

from app.settings import init_settings
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import os
from app.config import DATA_DIR
from app.api.chat import chat_router


load_dotenv()
init_settings()
environment = os.getenv("ENVIRONMENT", "development")

app = FastAPI()

# redirect to docs
@app.get("/")
def redirect_to_docs():
    return RedirectResponse(url="/docs")


def mount_files(directory: str, path: str):
    app.mount(
        path,
        StaticFiles(directory=directory, check_dir=False),
        name=f"{directory}_static",
    )


# load static files
mount_files(DATA_DIR, "/data")


app.include_router(chat_router, prefix="/api/chat")

if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "0.0.0.0")
    app_port = int(os.getenv("APP_PORT", "8000"))
    reload = True if environment == "development" else False

    uvicorn.run(app="main:app", host=app_host, port=app_port, reload=reload)
