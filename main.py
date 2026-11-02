"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers.plans import router as plans_router


def create_app() -> FastAPI:
    application = FastAPI(title="Pilgrimage Planner API")
    origins = settings.ALLOWED_ORIGINS or ["*"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(settings.ALLOWED_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(plans_router)
    # Must be mounted after API routes so the SPA does not swallow /api requests.
    application.mount("/", StaticFiles(directory="public", html=True), name="public")
    return application


app = create_app()
