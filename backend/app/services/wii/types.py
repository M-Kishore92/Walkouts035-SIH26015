"""
Watershed Impact Index (WII) — Core domain types.

These dataclasses are the contract between the data pipeline and the pure
WII engine. They carry no IO, no ORM fields, no database references.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WIIBand(str, Enum):
    """WII score interpretation bands."""
    CRITICAL = "CRITICAL"     # 0–25: Severe degradation or no improvement
    POOR = "POOR"             # 26–40: Minimal positive change
    MODERATE = "MODERATE"     # 41–55: Some improvement, below threshold
    GOOD = "GOOD"             # 56–70: Clear positive outcomes
    EXCELLENT = "EXCELLENT"   # 71–100: Exceptional watershed recovery


class ValidationStatus(str, Enum):
    """Cross-validation outcome for a satellite change claim."""
    PHOTO_CORROBORATED = "PHOTO_CORROBORATED"
    # Satellite change is backed by at least one matching field photo
    PARTIALLY_CORROBORATED = "PARTIALLY_CORROBORATED"
    # Some photos match, some contradict
    UNVERIFIED = "UNVERIFIED"
    # No DRISHTI photos exist within the spatial/temporal window
    FLAGGED_MISMATCH = "FLAGGED_MISMATCH"
    # Photos actively contradict the satellite-claimed change


@dataclass(frozen=True)
class SatelliteEpoch:
    """
    Satellite-derived measurements for one micro-watershed at one epoch.
    All area figures in hectares. All indices dimensionless (0–1 or -1 to 1).
    """
    watershed_id: str
    epoch: str                       # e.g., "T0", "T1", "T2", "T3", "T4", "T5"
    ndvi_mean: float                 # Mean NDVI over watershed polygon
    ndwi_mean: float                 # Mean NDWI over watershed polygon
    water_spread_ha: float           # Water-body extent in ha
    degraded_land_ha: float          # Degraded / barren land in ha
    total_area_ha: float             # Total micro-watershed area
    cloud_cover_fraction: float      # Fraction 0.0–1.0; high = unreliable epoch
    sensor: str = "Sentinel-2"
    resolution_m: int = 30


@dataclass(frozen=True)
class EpochDelta:
    """
    Change between two consecutive satellite epochs.
    Positive = improvement direction (more water, more vegetation, less degraded land).
    """
    watershed_id: str
    epoch_from: str
    epoch_to: str
    delta_ndvi: float                # T_n - T_{n-1}
    delta_water_spread_ha: float     # positive = more water
    delta_degraded_land_ha: float    # negative = less degraded (improvement)
    cloud_cover_fraction: float      # worst of the two epochs


@dataclass(frozen=True)
class PhotoValidation:
    """
    Cross-validation result for one satellite change claim within a watershed-epoch.
    This is the output of the Cross-Validation engine and the primary input
    to the WII engine's PhotoValidationConfidence component.
    """
    watershed_id: str
    epoch: str
    total_satellite_claims: int      # Number of change claims requiring photo corroboration
    corroborated_claims: int         # Claims backed by a matching photo tag
    contradicted_claims: int         # Claims actively contradicted by a photo tag
    unverified_claims: int           # Claims with no photo in the spatiotemporal window
    flagged_mismatches: int          # Contradicted claims that need field re-check

    @property
    def confidence(self) -> float:
        """
        Photo validation confidence: fraction of claims corroborated.
        Unverified ≠ contradicted — they get partial credit (0.5 weight).
        Returns value in [0.0, 1.0].
        """
        if self.total_satellite_claims == 0:
            return 0.5  # No claims = no penalty, no bonus
        numerator = self.corroborated_claims + 0.5 * self.unverified_claims
        return numerator / self.total_satellite_claims


@dataclass(frozen=True)
class CohortStats:
    """
    District/state cohort statistics for min-max normalization.
    Required by the WII engine to make scores comparable across watersheds.
    """
    ndvi_delta_min: float
    ndvi_delta_max: float
    water_delta_ha_min: float
    water_delta_ha_max: float
    degraded_delta_ha_min: float
    degraded_delta_ha_max: float


@dataclass(frozen=True)
class WIIResult:
    """Complete WII computation result — output of the pure engine."""
    watershed_id: str
    epoch_from: str
    epoch_to: str

    # Component scores (all in [0, 1])
    ndvi_score: float
    water_score: float
    degraded_score: float
    photo_confidence_score: float

    # Weighted composite
    wii_score: float                 # 0–100
    band: WIIBand

    # Metadata
    cloud_cover_warning: bool        # True if cloud_cover_fraction > 0.30
    data_gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
