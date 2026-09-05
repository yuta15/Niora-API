from fastapi import APIRouter

from src.api.v1.textbook.router import router as textbook_router

router = APIRouter(prefix="/v1")
router.include_router(textbook_router)
