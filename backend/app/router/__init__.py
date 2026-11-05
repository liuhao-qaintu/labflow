from fastapi import APIRouter
from app.router.auth import router as auth_router
from app.router.user import router as user_router
from app.router.upload import router as files_router
from app.router.lab import router as lab_router
from app.router.equipment import router as equipment_router
from app.router.reservation import router as reservation_router
from app.router.ai import router as ai_router
from app.router.recovery import router as recovery_router
router = APIRouter(prefix="/router")

router.include_router(auth_router)
router.include_router(user_router)
router.include_router(files_router)
router.include_router(lab_router)
router.include_router(equipment_router)
router.include_router(reservation_router)
router.include_router(ai_router)
router.include_router(recovery_router)
