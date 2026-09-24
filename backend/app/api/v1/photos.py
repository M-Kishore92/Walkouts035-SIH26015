"""
Photos API — upload, auto-tag, dedup, and query DRISHTI field photos.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import PhotoRecord, Watershed, User
from app.core.security import get_current_user
from app.workers.celery_app import ingest_photo_task
import structlog

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_photo(
    file: UploadFile = File(...),
    watershed_code: str = Form(...),
    epoch: str = Form(...),
    captured_at: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Upload a DRISHTI geo-tagged photo.
    Processing is async: CV tagging, blur detection, pHash dedup run in Celery.
    Returns a photo_id for status polling.
    """
    # Validate watershed exists
    watershed = await db.scalar(
        select(Watershed).where(Watershed.watershed_code == watershed_code)
    )
    if not watershed:
        raise HTTPException(status_code=404, detail=f"Watershed '{watershed_code}' not found")

    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Only JPEG/PNG/WebP images accepted")

    photo_id = f"DRSHT-{uuid.uuid4().hex[:12].upper()}"
    image_bytes = await file.read()

    # Queue async processing
    ingest_photo_task.apply_async(
        kwargs={
            "photo_id": photo_id,
            "watershed_id": str(watershed.id),
            "submitted_by": str(current_user.id),
            "image_bytes_b64": __import__("base64").b64encode(image_bytes).decode(),
            "captured_at": captured_at,
            "lat": lat,
            "lon": lon,
            "epoch": epoch,
            "filename": file.filename,
            "content_type": file.content_type,
        },
        queue="fast",
    )

    log.info("Photo queued for processing", photo_id=photo_id, watershed=watershed_code)
    return {
        "photo_id": photo_id,
        "status": "queued",
        "message": "Photo is being processed. Poll /photos/{photo_id}/status for updates.",
    }


@router.get("/{photo_id}")
async def get_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get full photo record including CV auto-tagger results."""
    photo = await db.scalar(select(PhotoRecord).where(PhotoRecord.photo_id == photo_id))
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return {
        "photo_id": photo.photo_id,
        "watershed_id": photo.watershed_id,
        "lat": photo.lat,
        "lon": photo.lon,
        "epoch": photo.epoch,
        "captured_at": photo.captured_at.isoformat() if photo.captured_at else None,
        "structure_type": photo.structure_type,
        "condition": photo.condition,
        "classifier_confidence": photo.classifier_confidence,
        "auto_caption": photo.auto_caption,
        "is_blurry": photo.is_blurry,
        "blur_score": photo.blur_score,
        "is_duplicate": photo.is_duplicate,
        "has_valid_exif": photo.has_valid_exif,
        "status": photo.status,
    }


@router.get("/{photo_id}/status")
async def get_photo_status(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Poll photo processing status."""
    photo = await db.scalar(select(PhotoRecord).where(PhotoRecord.photo_id == photo_id))
    if not photo:
        return {"photo_id": photo_id, "status": "pending", "message": "Processing queued"}
    return {"photo_id": photo_id, "status": photo.status}


@router.get("/watershed/{watershed_code}")
async def list_watershed_photos(
    watershed_code: str,
    epoch: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List all photos for a watershed, optionally filtered by epoch."""
    watershed = await db.scalar(
        select(Watershed).where(Watershed.watershed_code == watershed_code)
    )
    if not watershed:
        raise HTTPException(status_code=404, detail="Watershed not found")

    q = select(PhotoRecord).where(PhotoRecord.watershed_id == watershed.id)
    if epoch:
        q = q.where(PhotoRecord.epoch == epoch)
    q = q.limit(limit).offset(offset)

    photos = await db.scalars(q)
    items = [
        {
            "photo_id": p.photo_id,
            "lat": p.lat,
            "lon": p.lon,
            "epoch": p.epoch,
            "captured_at": p.captured_at.isoformat() if p.captured_at else None,
            "structure_type": p.structure_type,
            "condition": p.condition,
            "classifier_confidence": p.classifier_confidence,
            "status": p.status,
        }
        for p in photos.all()
    ]
    return {"watershed_code": watershed_code, "count": len(items), "photos": items}
