"""CV Studio API application factory and router registration."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import annotations, auth, compilations, cvs, health, jobs
from .services.compilation import shutdown_compiler


@asynccontextmanager
async def lifespan(_: FastAPI):
    # TODO(database-migrations): Replace create_all with Alembic migrations
    # before the first production deployment.
    Base.metadata.create_all(engine)
    yield
    shutdown_compiler()


def create_app() -> FastAPI:
    application = FastAPI(
        title="CV Studio API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (
        health.router,
        auth.router,
        cvs.router,
        compilations.router,
        annotations.router,
        jobs.router,
    ):
        application.include_router(router, prefix="/api")
    return application


app = create_app()
