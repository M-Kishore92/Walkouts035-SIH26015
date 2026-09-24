"""Reports API — generate and download IWMP monitoring reports."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import MonitoringReport, District, User
from app.core.security import get_current_user, require_role
from app.workers.celery_app import generate_report_task

router = APIRouter()


@router.post("/generate/{district_code}/{epoch_from}/{epoch_to}", status_code=202)
async def trigger_report_generation(
    district_code: str, epoch_from: str, epoch_to: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("monitor", "planner", "admin")),
) -> dict:
    d = await db.scalar(select(District).where(District.code == district_code))
    if not d:
        raise HTTPException(status_code=404, detail="District not found")
    generate_report_task.apply_async(
        kwargs={"district_id": str(d.id), "epoch_from": epoch_from, "epoch_to": epoch_to, "user_id": str(current_user.id)},
        queue="fast",
    )
    return {"status": "queued", "district_code": district_code}


@router.get("/district/{district_code}")
async def list_reports(
    district_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    d = await db.scalar(select(District).where(District.code == district_code))
    if not d:
        raise HTTPException(status_code=404, detail="District not found")
    reports = (await db.scalars(
        select(MonitoringReport).where(MonitoringReport.district_id == d.id).order_by(MonitoringReport.generated_at.desc()).limit(20)
    )).all()
    return {
        "district_code": district_code,
        "reports": [
            {"id": str(r.id), "epoch_from": r.epoch_from, "epoch_to": r.epoch_to,
             "avg_wii": r.avg_wii, "flagged_mismatches": r.flagged_mismatches,
             "generated_at": r.generated_at.isoformat() if r.generated_at else None}
            for r in reports
        ],
    }
