import asyncio
import logging
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import get_settings
from app.web.routes import router as web_router


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

settings = get_settings()

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title=settings.app_name,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router)
app.include_router(web_router)
