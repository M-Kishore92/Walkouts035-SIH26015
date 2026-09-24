"""
WII API — compute, retrieve, and compare Watershed Impact Index scores.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import WIIScore, Watershed, District, User
from app.core.security import get_current_user
from app.workers.celery_app import compute_wii_task
import structlog

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/compute/{watershed_code}/{epoch_from}/{epoch_to}", status_code=202)
async def trigger_wii_computation(
    watershed_code: str,
    epoch_from: str,
    epoch_to: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger WII computation for a watershed epoch transition."""
    watershed = await db.scalar(
        select(Watershed).where(Watershed.watershed_code == watershed_code)
    )
    if not watershed:
        raise HTTPException(status_code=404, detail="Watershed not found")

    compute_wii_task.apply_async(
        kwargs={"watershed_id": str(watershed.id), "epoch_from": epoch_from, "epoch_to": epoch_to},
        queue="fast",
    )
    return {"status": "queued", "watershed_code": watershed_code,
            "epoch_from": epoch_from, "epoch_to": epoch_to}


@router.get("/{watershed_code}")
async def get_wii_scores(
    watershed_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get all WII scores for a watershed across all epoch transitions."""
    watershed = await db.scalar(
        select(Watershed).where(Watershed.watershed_code == watershed_code)
    )
    if not watershed:
        raise HTTPException(status_code=404, detail="Watershed not found")

    scores_q = await db.scalars(
        select(WIIScore)
        .where(WIIScore.watershed_id == watershed.id)
        .order_by(WIIScore.epoch_to)
    )
    scores = scores_q.all()

    return {
        "watershed_code": watershed_code,
        "watershed_name": watershed.name,
        "area_ha": watershed.area_ha,
        "scores": [
            {
                "epoch_from": s.epoch_from,
                "epoch_to": s.epoch_to,
                "wii_score": s.wii_score,
                "band": s.band,
                "ndvi_score": s.ndvi_score,
                "water_score": s.water_score,
                "degraded_score": s.degraded_score,
                "photo_confidence_score": s.photo_confidence_score,
                "cloud_cover_warning": s.cloud_cover_warning,
                "notes": s.notes,
                "computed_at": s.computed_at.isoformat() if s.computed_at else None,
            }
            for s in scores
        ],
    }


@router.get("/district/{district_code}/ranking")
async def get_district_ranking(
    district_code: str,
    epoch_to: str = "T5",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Rank all watersheds in a district by their latest WII score.
    This is the primary output for planners to prioritize interventions.
    """
    district = await db.scalar(
        select(District).where(District.code == district_code)
    )
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT w.watershed_code, w.name, w.area_ha,
               ws.wii_score, ws.band, ws.epoch_from, ws.epoch_to,
               ws.photo_confidence_score, ws.cloud_cover_warning
        FROM watersheds w
        JOIN wii_scores ws ON ws.watershed_id = w.id
        WHERE w.district_id = :district_id
          AND ws.epoch_to = :epoch_to
        ORDER BY ws.wii_score DESC
    """), {"district_id": str(district.id), "epoch_to": epoch_to})

    rows = result.fetchall()
    return {
        "district_code": district_code,
        "epoch_to": epoch_to,
        "watershed_count": len(rows),
        "ranking": [
            {
                "rank": idx + 1,
                "watershed_code": r.watershed_code,
                "watershed_name": r.name,
                "area_ha": r.area_ha,
                "wii_score": r.wii_score,
                "band": r.band,
                "epoch_from": r.epoch_from,
                "photo_confidence_score": r.photo_confidence_score,
                "cloud_cover_warning": r.cloud_cover_warning,
            }
            for idx, r in enumerate(rows)
        ],
    }
