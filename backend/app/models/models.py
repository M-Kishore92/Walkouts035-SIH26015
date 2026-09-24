"""
SQLAlchemy ORM models for the Watershed Intelligence Platform.

All geometry columns are PostGIS geography type (WGS84 / EPSG:4326).
The adjudication_ledger table is hash-chained and append-only at the DB level.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Users & Roles ────────────────────────────────────────────────────────────

class User(Base):
    """Field officers, monitoring officers, planners, auditors."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(128))
    role = Column(String(32), nullable=False)  # field_officer | monitor | planner | auditor | admin
    district_code = Column(String(32))          # e.g. "nanded", "osmanabad"
    state_code = Column(String(8))              # e.g. "MH", "KA"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ── Geography ────────────────────────────────────────────────────────────────

class District(Base):
    __tablename__ = "districts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    state_code = Column(String(8), nullable=False)
    geom = Column(Geography("MULTIPOLYGON", srid=4326))
    watersheds = relationship("Watershed", back_populates="district")


class Watershed(Base):
    """
    Micro-watershed polygon — the atomic unit of the monitoring system.
    Corresponds to IWMP sub-watershed / Bhuvan polygon.
    """
    __tablename__ = "watersheds"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    watershed_code = Column(String(64), unique=True, nullable=False, index=True)
    # e.g., "IWMP-14-MW07"
    name = Column(String(128))
    district_id = Column(UUID(as_uuid=False), ForeignKey("districts.id"), nullable=False)
    geom = Column(Geography("POLYGON", srid=4326), nullable=False)
    area_ha = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    district = relationship("District", back_populates="watersheds")
    satellite_epochs = relationship("SatelliteEpochRecord", back_populates="watershed")
    photos = relationship("PhotoRecord", back_populates="watershed")
    wii_scores = relationship("WIIScore", back_populates="watershed")

    __table_args__ = (
        Index("ix_watersheds_district", "district_id"),
    )


# ── Photos ───────────────────────────────────────────────────────────────────

class PhotoRecord(Base):
    """
    A single DRISHTI geo-tagged photo with CV auto-tagger output.
    """
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    photo_id = Column(String(64), unique=True, nullable=False, index=True)
    # DRISHTI original ID, e.g., "DRSHT-2026-0091423"
    watershed_id = Column(UUID(as_uuid=False), ForeignKey("watersheds.id"), nullable=False)
    submitted_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    # Geolocation
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    gps_accuracy_m = Column(Float)
    location = Column(Geography("POINT", srid=4326))

    # Timestamps
    captured_at = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    epoch = Column(String(8))  # T0–T5

    # Storage
    minio_key = Column(String(256), nullable=False)
    file_size_bytes = Column(Integer)

    # EXIF metadata
    exif_data = Column(JSONB)
    has_valid_exif = Column(Boolean, default=False)

    # Photo quality gate
    blur_score = Column(Float)       # Laplacian variance; higher = sharper
    is_blurry = Column(Boolean, default=False)
    phash = Column(String(64))       # DCT perceptual hash for dedup
    is_duplicate = Column(Boolean, default=False)

    # CV auto-tagger output
    structure_type = Column(String(64))      # check_dam, farm_pond, etc.
    condition = Column(String(32))           # functional, damaged, silted, etc.
    classifier_confidence = Column(Float)
    auto_caption = Column(Text)
    tagger_model_version = Column(String(32))
    raw_predictions = Column(JSONB)          # All class probabilities

    # Processing status
    status = Column(String(32), default="pending")  # pending | processed | failed

    watershed = relationship("Watershed", back_populates="photos")

    __table_args__ = (
        Index("ix_photos_watershed_epoch", "watershed_id", "epoch"),
        Index("ix_photos_location", location, postgresql_using="gist"),
    )


# ── Satellite Processing ─────────────────────────────────────────────────────

class SatelliteEpochRecord(Base):
    """Satellite-derived measurements for one watershed at one epoch."""
    __tablename__ = "satellite_epochs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    watershed_id = Column(UUID(as_uuid=False), ForeignKey("watersheds.id"), nullable=False)
    epoch = Column(String(8), nullable=False)  # T0–T5
    epoch_start = Column(DateTime(timezone=True), nullable=False)
    epoch_end = Column(DateTime(timezone=True), nullable=False)

    # Computed indices
    ndvi_mean = Column(Float)
    ndvi_std = Column(Float)
    ndwi_mean = Column(Float)
    ndwi_std = Column(Float)
    water_spread_ha = Column(Float)
    degraded_land_ha = Column(Float)
    vegetation_ha = Column(Float)
    agriculture_ha = Column(Float)

    # Quality metadata
    cloud_cover_fraction = Column(Float, default=0.0)
    scene_count = Column(Integer, default=1)
    sensor = Column(String(32), default="Sentinel-2")
    resolution_m = Column(Integer, default=30)

    # LULC classification
    lulc_classes = Column(JSONB)   # {"water": 3.2, "vegetation": 45.1, ...}

    # Raster storage (COG keys in MinIO)
    ndvi_cog_key = Column(String(256))
    ndwi_cog_key = Column(String(256))
    lulc_cog_key = Column(String(256))

    processed_at = Column(DateTime(timezone=True), server_default=func.now())

    watershed = relationship("Watershed", back_populates="satellite_epochs")

    __table_args__ = (
        UniqueConstraint("watershed_id", "epoch", name="uq_satellite_epoch"),
        Index("ix_satellite_watershed_epoch", "watershed_id", "epoch"),
    )


# ── Cross-Validation ─────────────────────────────────────────────────────────

class SatelliteChangeClaim(Base):
    """One satellite-detected change claim requiring photo corroboration."""
    __tablename__ = "satellite_change_claims"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    watershed_id = Column(UUID(as_uuid=False), ForeignKey("watersheds.id"), nullable=False)
    epoch = Column(String(8), nullable=False)
    change_type = Column(String(32), nullable=False)
    # WATER_INCREASE | VEGETATION_INCREASE | DEGRADED_REDUCTION | LULC_SHIFT
    magnitude = Column(Float)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)

    # Cross-validation result
    outcome = Column(String(32))
    # PHOTO_CORROBORATED | PARTIALLY_CORROBORATED | UNVERIFIED | FLAGGED_MISMATCH
    corroborating_photo_ids = Column(JSONB, default=list)
    contradicting_photo_ids = Column(JSONB, default=list)
    notes = Column(JSONB, default=list)

    computed_at = Column(DateTime(timezone=True))


# ── WII Scores ───────────────────────────────────────────────────────────────

class WIIScore(Base):
    """Computed WII scores per watershed per epoch transition."""
    __tablename__ = "wii_scores"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    watershed_id = Column(UUID(as_uuid=False), ForeignKey("watersheds.id"), nullable=False)
    epoch_from = Column(String(8), nullable=False)
    epoch_to = Column(String(8), nullable=False)

    # Component scores
    ndvi_score = Column(Float)
    water_score = Column(Float)
    degraded_score = Column(Float)
    photo_confidence_score = Column(Float)

    # Composite
    wii_score = Column(Float, nullable=False)
    band = Column(String(16), nullable=False)

    # Metadata
    cloud_cover_warning = Column(Boolean, default=False)
    notes = Column(JSONB, default=list)
    data_gaps = Column(JSONB, default=list)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    watershed = relationship("Watershed", back_populates="wii_scores")

    __table_args__ = (
        UniqueConstraint("watershed_id", "epoch_from", "epoch_to", name="uq_wii_epoch"),
    )


# ── Reports ──────────────────────────────────────────────────────────────────

class MonitoringReport(Base):
    """Auto-generated IWMP-format monitoring reports."""
    __tablename__ = "monitoring_reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    district_id = Column(UUID(as_uuid=False), ForeignKey("districts.id"), nullable=False)
    epoch_from = Column(String(8), nullable=False)
    epoch_to = Column(String(8), nullable=False)
    title = Column(String(256))
    generated_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Storage
    docx_key = Column(String(256))
    pdf_key = Column(String(256))

    # Summary statistics
    total_watersheds = Column(Integer)
    avg_wii = Column(Float)
    flagged_mismatches = Column(Integer)
    summary_stats = Column(JSONB)


# ── Adjudication Ledger (Hash-Chained, Append-Only) ──────────────────────────

class AdjudicationEntry(Base):
    """
    Immutable adjudication record. Append-only at DB level (UPDATE/DELETE revoked).
    Every entry is SHA-256 hash-chained to the previous entry.
    """
    __tablename__ = "adjudication_ledger"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    sequence_number = Column(Integer, nullable=False, unique=True)
    claim_id = Column(UUID(as_uuid=False), ForeignKey("satellite_change_claims.id"), nullable=False)
    officer_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    decision = Column(String(16), nullable=False)  # ACCEPT | REJECT | DEFER
    decision_notes = Column(Text)
    officer_signature = Column(String(256))        # Officer's digital signature (JWT)
    decided_at = Column(DateTime(timezone=True), nullable=False)

    # Hash chain
    payload_hash = Column(String(64), nullable=False)     # SHA-256 of this entry's payload
    previous_hash = Column(String(64), nullable=False)    # SHA-256 of previous entry (0000...0 for genesis)
    chain_hash = Column(String(64), nullable=False)       # SHA-256(payload_hash + previous_hash)

    __table_args__ = (
        Index("ix_ledger_sequence", "sequence_number"),
    )
