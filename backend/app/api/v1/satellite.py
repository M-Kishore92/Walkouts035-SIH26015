"""Satellite API — trigger processing and view epoch results."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import SatelliteEpochRecord, Watershed, User
from app.core.security import get_current_user
from app.workers.celery_app import process_satellite_epoch

router = APIRouter()


@router.post("/process/{watershed_code}/{epoch}", status_code=202)
async def trigger_satellite_processing(
    watershed_code: str, epoch: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    w = await db.scalar(select(Watershed).where(Watershed.watershed_code == watershed_code))
    if not w:
        raise HTTPException(status_code=404, detail="Watershed not found")
    process_satellite_epoch.apply_async(
        kwargs={"watershed_id": str(w.id), "epoch": epoch}, queue="satellite"
    )
    return {"status": "queued", "watershed_code": watershed_code, "epoch": epoch}


@router.get("/{watershed_code}/epochs")
async def get_satellite_epochs(
    watershed_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    w = await db.scalar(select(Watershed).where(Watershed.watershed_code == watershed_code))
    if not w:
        raise HTTPException(status_code=404, detail="Watershed not found")
    epochs = (await db.scalars(
        select(SatelliteEpochRecord).where(SatelliteEpochRecord.watershed_id == w.id).order_by(SatelliteEpochRecord.epoch)
    )).all()
    return {
        "watershed_code": watershed_code,
        "epochs": [
            {
                "epoch": e.epoch, "ndvi_mean": e.ndvi_mean, "ndwi_mean": e.ndwi_mean,
                "water_spread_ha": e.water_spread_ha, "degraded_land_ha": e.degraded_land_ha,
                "cloud_cover_fraction": e.cloud_cover_fraction, "sensor": e.sensor,
                "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            }
            for e in epochs
        ],
    }
