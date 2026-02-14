from fastapi import APIRouter

from .conversations import router as conversations_router
from .polling import router as polling_router
from .stats import router as stats_router

router = APIRouter()
router.include_router(conversations_router)
router.include_router(polling_router)
router.include_router(stats_router)
