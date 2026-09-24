"""
API v1 router — aggregates all endpoint modules.
"""
from fastapi import APIRouter

from app.api.v1 import auth, photos, watersheds, satellite, crossval, wii, reports, ledger, admin

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(photos.router, prefix="/photos", tags=["photos"])
router.include_router(watersheds.router, prefix="/watersheds", tags=["watersheds"])
router.include_router(satellite.router, prefix="/satellite", tags=["satellite"])
router.include_router(crossval.router, prefix="/crossval", tags=["cross-validation"])
router.include_router(wii.router, prefix="/wii", tags=["wii"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(ledger.router, prefix="/ledger", tags=["ledger"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
