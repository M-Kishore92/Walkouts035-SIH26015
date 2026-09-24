"""
Celery Application — Dual Queue Architecture.

Queues:
  'fast'      → Quick tasks: photo ingest, EXIF, blur/hash, CV inference, cross-val, WII
  'satellite' → Heavy tasks: Sentinel-2 COG fetch, NDVI/NDWI/LULC computation

Workers are started with:
  celery -A app.workers.celery_app worker --loglevel=info -Q fast,satellite -c 4
"""
from __future__ import annotations

import base64
import hashlib
import io
from datetime import datetime, timezone

import structlog
from celery import Celery

from app.core.config import settings

log = structlog.get_logger(__name__)

celery_app = Celery(
    "watershed",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.celery_app.ingest_photo_task": {"queue": "fast"},
        "app.workers.celery_app.compute_wii_task": {"queue": "fast"},
        "app.workers.celery_app.run_crossval_task": {"queue": "fast"},
        "app.workers.celery_app.process_satellite_epoch": {"queue": "satellite"},
        "app.workers.celery_app.generate_report_task": {"queue": "fast"},
    },
    beat_schedule={
        "refresh-flagged-queue": {
            "task": "app.workers.celery_app.refresh_verification_queue",
            "schedule": 3600,  # hourly
        },
    },
)


# ── Photo Ingestion Task ──────────────────────────────────────────────────────

@celery_app.task(name="app.workers.celery_app.ingest_photo_task", bind=True, max_retries=3)
def ingest_photo_task(
    self,
    photo_id: str,
    watershed_id: str,
    submitted_by: str,
    image_bytes_b64: str,
    captured_at: str,
    lat: float,
    lon: float,
    epoch: str,
    filename: str,
    content_type: str,
) -> dict:
    """
    Fast queue: ingest a DRISHTI photo.
    Steps:
      1. Upload to MinIO
      2. Extract EXIF metadata
      3. Run Laplacian blur detection
      4. Compute pHash for deduplication
      5. Run CV auto-tagger (MobileNetV3 / ONNX)
      6. Persist PhotoRecord to PostgreSQL
      7. Trigger cross-validation for the watershed-epoch
    """
    try:
        log.info("Ingesting photo", photo_id=photo_id)
        image_bytes = base64.b64decode(image_bytes_b64)

        # Step 1–4: Photo quality analysis
        from app.services.photo.analyzer import analyze_photo
        analysis = analyze_photo(photo_id, image_bytes)

        # Step 5: CV inference
        from app.services.photo.tagger import tag_structure
        tagging = tag_structure(image_bytes)

        # Step 6: Persist (sync via synchronous SQLAlchemy for Celery)
        from app.db.sync_session import get_sync_db
        from app.models.models import PhotoRecord

        with get_sync_db() as db:
            photo = PhotoRecord(
                photo_id=photo_id,
                watershed_id=watershed_id,
                submitted_by=submitted_by,
                lat=lat,
                lon=lon,
                captured_at=datetime.fromisoformat(captured_at),
                epoch=epoch,
                minio_key=analysis.minio_key,
                file_size_bytes=len(image_bytes),
                exif_data=analysis.exif_data,
                has_valid_exif=analysis.has_valid_exif,
                blur_score=analysis.blur_score,
                is_blurry=analysis.is_blurry,
                phash=analysis.phash,
                is_duplicate=analysis.is_duplicate,
                structure_type=tagging.structure_type,
                condition=tagging.condition,
                classifier_confidence=tagging.confidence,
                auto_caption=tagging.caption,
                tagger_model_version=tagging.model_version,
                raw_predictions=tagging.raw_predictions,
                status="processed",
            )
            db.add(photo)
            db.commit()

        # Step 7: Trigger cross-validation
        run_crossval_task.apply_async(
            kwargs={"watershed_id": watershed_id, "epoch": epoch},
            queue="fast",
            countdown=5,  # Short delay to let DB settle
        )

        log.info("Photo ingested successfully", photo_id=photo_id, structure=tagging.structure_type)
        return {"photo_id": photo_id, "status": "processed", "structure_type": tagging.structure_type}

    except Exception as exc:
        log.error("Photo ingestion failed", photo_id=photo_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# ── Cross-Validation Task ─────────────────────────────────────────────────────

@celery_app.task(name="app.workers.celery_app.run_crossval_task", bind=True, max_retries=2)
def run_crossval_task(self, watershed_id: str, epoch: str) -> dict:
    """
    Fast queue: run cross-validation for all satellite change claims
    in a watershed-epoch against available DRISHTI photos.
    """
    try:
        log.info("Running cross-validation", watershed_id=watershed_id, epoch=epoch)

        from app.db.sync_session import get_sync_db
        from app.models.models import SatelliteChangeClaim as ClaimModel, PhotoRecord
        from app.services.crossval.engine import (
            validate_watershed_epoch,
            SatelliteChangeClaim as ClaimDomain,
            PhotoRecord as PhotoDomain,
            ChangeType, StructureType, ConditionClass,
        )
        from app.core.config import settings
        from sqlalchemy import select, text

        with get_sync_db() as db:
            # Fetch claims
            claims_orm = db.execute(
                select(ClaimModel).where(
                    ClaimModel.watershed_id == watershed_id,
                    ClaimModel.epoch == epoch,
                )
            ).scalars().all()

            if not claims_orm:
                return {"watershed_id": watershed_id, "epoch": epoch, "claims": 0}

            # Fetch photos with pre-computed distances
            photos_raw = db.execute(text("""
                SELECT p.photo_id, p.structure_type, p.condition,
                       p.classifier_confidence,
                       ST_Distance(p.location::geography,
                         ST_Centroid(w.geom::geometry)::geography) AS distance_m,
                       0 AS days_from_epoch
                FROM photos p
                JOIN watersheds w ON w.id = p.watershed_id
                WHERE p.watershed_id = :wid AND p.epoch = :epoch
                  AND p.status = 'processed' AND p.is_duplicate = false
            """), {"wid": watershed_id, "epoch": epoch}).fetchall()

            # Convert to domain objects
            claims = [
                ClaimDomain(
                    claim_id=str(c.id),
                    watershed_id=watershed_id,
                    epoch=epoch,
                    change_type=ChangeType(c.change_type),
                    magnitude=c.magnitude or 0.0,
                    centroid_lat=c.centroid_lat or 0.0,
                    centroid_lon=c.centroid_lon or 0.0,
                )
                for c in claims_orm
            ]

            photos = [
                PhotoDomain(
                    photo_id=p.photo_id,
                    structure_type=StructureType(p.structure_type or "degraded_barren_land"),
                    condition=ConditionClass(p.condition or "unknown"),
                    confidence=p.classifier_confidence or 0.0,
                    distance_m=float(p.distance_m or 0),
                    days_from_epoch=int(p.days_from_epoch or 0),
                )
                for p in photos_raw
                if p.structure_type  # Skip untagged photos
            ]

            # Run pure cross-validation engine
            summary = validate_watershed_epoch(
                watershed_id=watershed_id,
                epoch=epoch,
                claims=claims,
                photos=photos,
                spatial_buffer_m=settings.CROSSVAL_SPATIAL_BUFFER_M,
                temporal_window_days=settings.CROSSVAL_TEMPORAL_WINDOW_DAYS,
            )

            # Persist results
            for result in summary.results:
                db.execute(text("""
                    UPDATE satellite_change_claims
                    SET outcome = :outcome,
                        corroborating_photo_ids = :corr,
                        contradicting_photo_ids = :contra,
                        notes = :notes,
                        computed_at = NOW()
                    WHERE id = :claim_id
                """), {
                    "outcome": result.outcome,
                    "corr": result.corroborating_photo_ids,
                    "contra": result.contradicting_photo_ids,
                    "notes": result.notes,
                    "claim_id": result.claim_id,
                })
            db.commit()

        # Trigger WII recomputation
        compute_wii_task.apply_async(
            kwargs={"watershed_id": watershed_id, "epoch_from": _prev_epoch(epoch), "epoch_to": epoch},
            queue="fast",
            countdown=10,
        )

        return {
            "watershed_id": watershed_id,
            "epoch": epoch,
            "total_claims": summary.total_claims,
            "flagged": summary.flagged_mismatches,
        }
    except Exception as exc:
        log.error("Cross-validation failed", watershed_id=watershed_id, epoch=epoch, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


def _prev_epoch(epoch: str) -> str:
    """Return the previous epoch label (T3 → T2, T0 → T0)."""
    mapping = {"T1": "T0", "T2": "T1", "T3": "T2", "T4": "T3", "T5": "T4"}
    return mapping.get(epoch, "T0")


# ── WII Computation Task ──────────────────────────────────────────────────────

@celery_app.task(name="app.workers.celery_app.compute_wii_task", bind=True, max_retries=2)
def compute_wii_task(self, watershed_id: str, epoch_from: str, epoch_to: str) -> dict:
    """Fast queue: compute WII for a watershed epoch transition."""
    try:
        from app.db.sync_session import get_sync_db
        from app.models.models import SatelliteEpochRecord, SatelliteChangeClaim, WIIScore
        from app.services.wii.engine import compute_wii
        from app.services.wii.types import (
            EpochDelta, PhotoValidation, CohortStats
        )
        from sqlalchemy import select, func, text

        with get_sync_db() as db:
            # Get both epochs
            ep_from = db.execute(
                select(SatelliteEpochRecord).where(
                    SatelliteEpochRecord.watershed_id == watershed_id,
                    SatelliteEpochRecord.epoch == epoch_from,
                )
            ).scalar_one_or_none()

            ep_to = db.execute(
                select(SatelliteEpochRecord).where(
                    SatelliteEpochRecord.watershed_id == watershed_id,
                    SatelliteEpochRecord.epoch == epoch_to,
                )
            ).scalar_one_or_none()

            if not ep_from or not ep_to:
                log.warning("Missing epochs for WII", watershed_id=watershed_id)
                return {"status": "skipped", "reason": "missing_epochs"}

            # Get cross-val summary
            claims_q = db.execute(
                select(SatelliteChangeClaim).where(
                    SatelliteChangeClaim.watershed_id == watershed_id,
                    SatelliteChangeClaim.epoch == epoch_to,
                )
            ).scalars().all()

            total_claims = len(claims_q)
            corroborated = sum(1 for c in claims_q if c.outcome == "PHOTO_CORROBORATED")
            flagged = sum(1 for c in claims_q if c.outcome == "FLAGGED_MISMATCH")

            photo_val = PhotoValidation(
                watershed_id=watershed_id,
                epoch=epoch_to,
                total_satellite_claims=total_claims,
                corroborated_claims=corroborated,
                contradicted_claims=flagged,
                unverified_claims=sum(1 for c in claims_q if c.outcome == "UNVERIFIED"),
                flagged_mismatches=flagged,
            )

            # Cohort stats (district-level min/max)
            cohort_raw = db.execute(text("""
                SELECT
                  MIN(t.delta_ndvi) as ndvi_min, MAX(t.delta_ndvi) as ndvi_max,
                  MIN(t.delta_water) as water_min, MAX(t.delta_water) as water_max,
                  MIN(t.delta_degraded) as deg_min, MAX(t.delta_degraded) as deg_max
                FROM (
                  SELECT
                    a.ndvi_mean - b.ndvi_mean AS delta_ndvi,
                    a.water_spread_ha - b.water_spread_ha AS delta_water,
                    a.degraded_land_ha - b.degraded_land_ha AS delta_degraded
                  FROM satellite_epochs a
                  JOIN satellite_epochs b ON b.watershed_id = a.watershed_id
                    AND b.epoch = :epoch_from
                  WHERE a.epoch = :epoch_to
                ) t
            """), {"epoch_from": epoch_from, "epoch_to": epoch_to}).fetchone()

            cohort = CohortStats(
                ndvi_delta_min=float(cohort_raw.ndvi_min or -0.3),
                ndvi_delta_max=float(cohort_raw.ndvi_max or 0.3),
                water_delta_ha_min=float(cohort_raw.water_min or -50),
                water_delta_ha_max=float(cohort_raw.water_max or 50),
                degraded_delta_ha_min=float(cohort_raw.deg_min or -100),
                degraded_delta_ha_max=float(cohort_raw.deg_max or 100),
            )

            delta = EpochDelta(
                watershed_id=watershed_id,
                epoch_from=epoch_from,
                epoch_to=epoch_to,
                delta_ndvi=ep_to.ndvi_mean - ep_from.ndvi_mean,
                delta_water_spread_ha=ep_to.water_spread_ha - ep_from.water_spread_ha,
                delta_degraded_land_ha=ep_to.degraded_land_ha - ep_from.degraded_land_ha,
                cloud_cover_fraction=max(
                    ep_from.cloud_cover_fraction or 0.0,
                    ep_to.cloud_cover_fraction or 0.0,
                ),
            )

            # Pure computation
            result = compute_wii(delta, photo_val, cohort)

            # Persist
            existing = db.execute(
                select(WIIScore).where(
                    WIIScore.watershed_id == watershed_id,
                    WIIScore.epoch_from == epoch_from,
                    WIIScore.epoch_to == epoch_to,
                )
            ).scalar_one_or_none()

            if existing:
                existing.wii_score = result.wii_score
                existing.band = result.band.value
                existing.ndvi_score = result.ndvi_score
                existing.water_score = result.water_score
                existing.degraded_score = result.degraded_score
                existing.photo_confidence_score = result.photo_confidence_score
                existing.cloud_cover_warning = result.cloud_cover_warning
                existing.notes = result.notes
                existing.data_gaps = result.data_gaps
            else:
                db.add(WIIScore(
                    watershed_id=watershed_id,
                    epoch_from=epoch_from,
                    epoch_to=epoch_to,
                    wii_score=result.wii_score,
                    band=result.band.value,
                    ndvi_score=result.ndvi_score,
                    water_score=result.water_score,
                    degraded_score=result.degraded_score,
                    photo_confidence_score=result.photo_confidence_score,
                    cloud_cover_warning=result.cloud_cover_warning,
                    notes=result.notes,
                    data_gaps=result.data_gaps,
                ))
            db.commit()

        log.info("WII computed", watershed_id=watershed_id, wii=result.wii_score, band=result.band)
        return {"wii_score": result.wii_score, "band": result.band.value}

    except Exception as exc:
        log.error("WII computation failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


# ── Satellite Processing Task ─────────────────────────────────────────────────

@celery_app.task(name="app.workers.celery_app.process_satellite_epoch", bind=True, max_retries=2)
def process_satellite_epoch(self, watershed_id: str, epoch: str) -> dict:
    """
    Satellite queue: fetch Sentinel-2 / GEE imagery and compute
    NDVI, NDWI, and LULC for a watershed-epoch.
    """
    try:
        log.info("Processing satellite epoch", watershed_id=watershed_id, epoch=epoch)
        from app.services.satellite.pipeline import compute_satellite_epoch
        result = compute_satellite_epoch(watershed_id, epoch)
        return result
    except Exception as exc:
        log.error("Satellite processing failed", error=str(exc))
        raise self.retry(exc=exc, countdown=120)


# ── Report Generation Task ────────────────────────────────────────────────────

@celery_app.task(name="app.workers.celery_app.generate_report_task", bind=True, max_retries=1)
def generate_report_task(self, district_id: str, epoch_from: str, epoch_to: str, user_id: str) -> dict:
    """Fast queue: generate and store IWMP monitoring report."""
    try:
        log.info("Generating report", district_id=district_id)
        from app.services.report.service import build_and_store_report
        report_id = build_and_store_report(district_id, epoch_from, epoch_to, user_id)
        return {"report_id": report_id, "status": "generated"}
    except Exception as exc:
        log.error("Report generation failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# ── Beat Task ─────────────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.celery_app.refresh_verification_queue")
def refresh_verification_queue() -> None:
    """Hourly: refresh materialized view of flagged mismatches."""
    log.info("Refreshing verification queue materialized view")
    try:
        from app.db.sync_session import get_sync_db
        from sqlalchemy import text
        with get_sync_db() as db:
            db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY verification_queue_mv"))
            db.commit()
    except Exception as exc:
        log.warning("Could not refresh materialized view", error=str(exc))
