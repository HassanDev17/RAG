from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.exceptions import AppException, app_exception_handler

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "ok"}
