import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import Base, engine
from database.seed import seed_default_listings
from .api.router import router
from .browser.monitor import monitor

# Import models so they register with Base
from . import models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_default_listings()
    logger.info("Messaging service started")
    yield

    # Shutdown: stop monitor and cleanup
    if monitor.running:
        await monitor.stop()
    logger.info("Messaging service stopped")
    await engine.dispose()


app = FastAPI(
    title="Bye-Buy Messaging Service",
    description="Facebook Marketplace auto-responder",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def read_root():
    return {"service": "messaging", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
