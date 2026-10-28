
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app import models  # Register SQLAlchemy models
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Backend API for the Rentozz equipment-rental marketplace.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "service": "Rentozz API",
        "status": "running",
        "docs": "/docs",
    }
