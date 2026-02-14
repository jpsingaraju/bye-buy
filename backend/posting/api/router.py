from fastapi import APIRouter

from .listings import router as listings_router
from .jobs import router as jobs_router

router = APIRouter(prefix="/api")
router.include_router(listings_router)
router.include_router(jobs_router)
