import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.router import router
from database.connection import Base, engine
from .config import settings
from .queue.worker import worker

# Import platform posters to register them
from . import platforms  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure upload directory exists
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # Start background worker
    await worker.start()
    logger.info("Background worker started")

    yield

    # Shutdown: stop worker and cleanup
    await worker.stop()
    logger.info("Background worker stopped")
    await engine.dispose()


app = FastAPI(
    title="Bye-Buy Posting Service",
    description="Multi-platform listing automation service",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for serving images
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# Include API router
app.include_router(router)


@app.get("/")
def read_root():
    return {"service": "posting", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
