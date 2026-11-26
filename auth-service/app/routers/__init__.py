from fastapi import APIRouter

from app.routers import auth, internal, users


router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(internal.router)
