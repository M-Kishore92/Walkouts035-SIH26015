"""
Cross-Validation API — view and trigger cross-validation of satellite claims.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import SatelliteChangeClaim, Watershed, User
from app.core.security import get_current_user
from app.workers.celery_app import run_crossval_task

router = APIRouter()


@router.post("/trigger/{watershed_code}/{epoch}", status_code=202)
async def trigger_crossval(
    watershed_code: str,
    epoch: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger cross-validation for all satellite claims in a watershed-epoch."""
    watershed = await db.scalar(
        select(Watershed).where(Watershed.watershed_code == watershed_code)
    )
    if not watershed:
        raise HTTPException(status_code=404, detail="Watershed not found")

    run_crossval_task.apply_async(
        kwargs={"watershed_id": str(watershed.id), "epoch": epoch},
        queue="fast",
    )
    return {"status": "queued", "watershed_code": watershed_code, "epoch": epoch}


@router.get("/watershed/{watershed_code}/{epoch}")
async def get_crossval_results(
    watershed_code: str,
    epoch: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get all cross-validation results for a watershed-epoch."""
    watershed = await db.scalar(
        select(Watershed).where(Watershed.watershed_code == watershed_code)
    )
    if not watershed:
        raise HTTPException(status_code=404, detail="Watershed not found")

    claims_q = await db.scalars(
        select(SatelliteChangeClaim)
        .where(
            SatelliteChangeClaim.watershed_id == watershed.id,
            SatelliteChangeClaim.epoch == epoch,
        )
    )
    claims = claims_q.all()

    total = len(claims)
    corroborated = sum(1 for c in claims if c.outcome == "PHOTO_CORROBORATED")
    flagged = sum(1 for c in claims if c.outcome == "FLAGGED_MISMATCH")

    return {
        "watershed_code": watershed_code,
        "epoch": epoch,
        "total_claims": total,
        "corroborated": corroborated,
        "flagged_mismatches": flagged,
        "photo_validation_confidence": (
            (corroborated + 0.5 * sum(1 for c in claims if c.outcome == "PARTIALLY_CORROBORATED"))
            / max(1, total)
        ),
        "claims": [
            {
                "claim_id": str(c.id),
                "change_type": c.change_type,
                "magnitude": c.magnitude,
                "outcome": c.outcome,
                "corroborating_photos": c.corroborating_photo_ids,
                "contradicting_photos": c.contradicting_photo_ids,
                "notes": c.notes,
            }
            for c in claims
        ],
    }


@router.get("/queue/flagged")
async def get_verification_queue(
    district_code: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Field Verification Queue: all FLAGGED_MISMATCH claims requiring human review.
    This is the primary action view for monitoring officers.
    """
    from sqlalchemy import text
    params: dict = {"limit": limit}
    district_filter = ""
    if district_code:
        district_filter = "AND d.code = :district_code"
        params["district_code"] = district_code

    result = await db.execute(text(f"""
        SELECT scc.id, scc.watershed_id, scc.epoch, scc.change_type,
               scc.magnitude, scc.outcome, scc.notes,
               w.watershed_code, w.name as watershed_name,
               d.name as district_name
        FROM satellite_change_claims scc
        JOIN watersheds w ON w.id = scc.watershed_id
        JOIN districts d ON d.id = w.district_id
        WHERE scc.outcome = 'FLAGGED_MISMATCH'
        {district_filter}
        ORDER BY scc.computed_at DESC
        LIMIT :limit
    """), params)

    rows = result.fetchall()
    return {
        "queue_size": len(rows),
        "items": [
            {
                "claim_id": str(r.id),
                "watershed_code": r.watershed_code,
                "watershed_name": r.watershed_name,
                "district_name": r.district_name,
                "epoch": r.epoch,
                "change_type": r.change_type,
                "magnitude": r.magnitude,
                "notes": r.notes,
            }
            for r in rows
        ],
    }
