"""
Cross-Validation Engine — Pure Functional Core.

CONTRACT: This module MUST remain free of all IO. The following are banned:
  - datetime, time, random
  - requests, httpx, aiohttp (no network)
  - open(), pathlib.Path.read*(), os.*
  - SQLAlchemy, asyncpg

Enforced by AST inspection in tests/unit/test_crossval_purity.py

LOGIC:
  For each satellite-claimed change in a micro-watershed epoch:
    1. Check if DRISHTI photos exist within SPATIAL_BUFFER_M metres and
       TEMPORAL_WINDOW_DAYS days of the epoch boundary.
    2. For each candidate photo, check if its structure_type + condition
       is corroborating or contradicting:
         - CORROBORATE: structure type matches expected improvement type AND
                        condition is "functional" or "under_construction"
         - CONTRADICT:  structure type matches expected improvement type AND
                        condition is "damaged" / "silted" / "dry"
                        OR photo-tagged land type directly contradicts satellite
         - UNVERIFIED:  no photos in the spatiotemporal window
    3. Return a CrossValResult with counts per category.

SPATIAL MATCHING (pure):
  Uses Haversine distance. Does NOT call PostGIS — the database layer
  passes pre-computed distances as floats.

TEMPORAL MATCHING (pure):
  Epoch boundaries passed as ISO date strings → parsed to ordinal ints.
  No datetime import — uses a pure ordinal parser.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


# ── Domain types ─────────────────────────────────────────────────────────────

class ChangeType(str, Enum):
    """Type of satellite-detected land/water change requiring photo corroboration."""
    WATER_INCREASE = "WATER_INCREASE"
    VEGETATION_INCREASE = "VEGETATION_INCREASE"
    DEGRADED_REDUCTION = "DEGRADED_REDUCTION"
    LULC_SHIFT = "LULC_SHIFT"


class StructureType(str, Enum):
    CHECK_DAM = "check_dam"
    FARM_POND = "farm_pond"
    CONTOUR_TRENCH = "contour_trench"
    GULLY_PLUG = "gully_plug"
    PERCOLATION_TANK = "percolation_tank"
    PLANTATION = "plantation"
    AFFORESTATION = "afforestation"
    LIVELIHOOD = "livelihood_structure"
    WATER_BODY = "water_body"
    AGRICULTURE = "agriculture_field"
    DEGRADED = "degraded_barren_land"


class ConditionClass(str, Enum):
    FUNCTIONAL = "functional"
    UNDER_CONSTRUCTION = "under_construction"
    DAMAGED = "damaged"
    SILTED = "silted"
    DRY = "dry"
    UNKNOWN = "unknown"


class PhotoOutcome(str, Enum):
    CORROBORATES = "CORROBORATES"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"        # Photo exists but is unrelated to the change type


@dataclass(frozen=True)
class PhotoRecord:
    """
    A single DRISHTI photo record, pre-processed for cross-validation.
    Distances/ordinals are computed by the database layer; engine is pure.
    """
    photo_id: str
    structure_type: StructureType
    condition: ConditionClass
    confidence: float            # Classifier confidence [0, 1]
    distance_m: float            # Pre-computed Haversine distance to change polygon centroid
    days_from_epoch: int         # Absolute days from the epoch boundary (signed, but |days| used)


@dataclass(frozen=True)
class SatelliteChangeClaim:
    """One satellite-detected change that requires photo corroboration."""
    claim_id: str
    watershed_id: str
    epoch: str
    change_type: ChangeType
    magnitude: float             # Area in ha or delta index value
    centroid_lat: float
    centroid_lon: float


@dataclass(frozen=True)
class CrossValResult:
    """
    Cross-validation outcome for one satellite change claim.
    Immutable output of the pure engine.
    """
    claim_id: str
    watershed_id: str
    epoch: str
    change_type: ChangeType
    outcome: str                         # PHOTO_CORROBORATED / PARTIALLY_CORROBORATED / UNVERIFIED / FLAGGED_MISMATCH
    corroborating_photo_ids: list[str] = field(default_factory=list)
    contradicting_photo_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WatershedCrossValSummary:
    """Aggregate cross-validation summary for one watershed-epoch."""
    watershed_id: str
    epoch: str
    total_claims: int
    corroborated: int
    partially_corroborated: int
    unverified: int
    flagged_mismatches: int
    results: list[CrossValResult] = field(default_factory=list)

    @property
    def photo_validation_confidence(self) -> float:
        """Confidence score to feed into WII engine."""
        if self.total_claims == 0:
            return 0.5
        numerator = self.corroborated + 0.5 * self.partially_corroborated + 0.25 * self.unverified
        return min(1.0, numerator / self.total_claims)


# ── Corroboration rules (pure lookup table) ───────────────────────────────────

# Maps change_type → (corroborating structure types, contradicting structure types)
_CORROBORATION_RULES: dict[ChangeType, tuple[frozenset[StructureType], frozenset[StructureType]]] = {
    ChangeType.WATER_INCREASE: (
        frozenset({StructureType.CHECK_DAM, StructureType.FARM_POND,
                   StructureType.PERCOLATION_TANK, StructureType.WATER_BODY}),
        frozenset({StructureType.DEGRADED}),
    ),
    ChangeType.VEGETATION_INCREASE: (
        frozenset({StructureType.PLANTATION, StructureType.AFFORESTATION,
                   StructureType.CONTOUR_TRENCH, StructureType.GULLY_PLUG,
                   StructureType.AGRICULTURE}),
        frozenset({StructureType.DEGRADED}),
    ),
    ChangeType.DEGRADED_REDUCTION: (
        frozenset({StructureType.PLANTATION, StructureType.AFFORESTATION,
                   StructureType.CONTOUR_TRENCH, StructureType.GULLY_PLUG}),
        frozenset({StructureType.DEGRADED}),
    ),
    ChangeType.LULC_SHIFT: (
        frozenset({StructureType.AGRICULTURE, StructureType.PLANTATION,
                   StructureType.WATER_BODY}),
        frozenset(),
    ),
}

# Conditions that corroborate vs. contradict
_GOOD_CONDITIONS: frozenset[ConditionClass] = frozenset({
    ConditionClass.FUNCTIONAL, ConditionClass.UNDER_CONSTRUCTION
})
_BAD_CONDITIONS: frozenset[ConditionClass] = frozenset({
    ConditionClass.DAMAGED, ConditionClass.SILTED, ConditionClass.DRY
})


def _classify_photo(
    photo: PhotoRecord,
    change_type: ChangeType,
    spatial_buffer_m: float,
    temporal_window_days: int,
) -> PhotoOutcome:
    """
    Classify one photo as CORROBORATES / CONTRADICTS / NEUTRAL.
    Pure function — no side effects.
    """
    # Must be within spatial and temporal windows
    if photo.distance_m > spatial_buffer_m:
        return PhotoOutcome.NEUTRAL
    if abs(photo.days_from_epoch) > temporal_window_days:
        return PhotoOutcome.NEUTRAL

    corr_types, contra_types = _CORROBORATION_RULES.get(
        change_type, (frozenset(), frozenset())
    )

    structure = photo.structure_type

    if structure in corr_types:
        if photo.condition in _GOOD_CONDITIONS:
            return PhotoOutcome.CORROBORATES
        elif photo.condition in _BAD_CONDITIONS:
            return PhotoOutcome.CONTRADICTS
        else:
            return PhotoOutcome.NEUTRAL  # condition unknown → don't penalise

    if structure in contra_types and photo.condition in _BAD_CONDITIONS:
        return PhotoOutcome.CONTRADICTS

    return PhotoOutcome.NEUTRAL


def validate_claim(
    claim: SatelliteChangeClaim,
    photos: Sequence[PhotoRecord],
    spatial_buffer_m: float = 500.0,
    temporal_window_days: int = 90,
) -> CrossValResult:
    """
    Cross-validate a single satellite change claim against available photo evidence.

    Arguments:
        claim:                  One satellite-detected change.
        photos:                 All DRISHTI photos pre-filtered to the watershed
                                (with pre-computed distances and day offsets).
        spatial_buffer_m:       Maximum distance (metres) for a photo to count.
        temporal_window_days:   Maximum days before/after epoch boundary.

    Returns:
        CrossValResult — pure, immutable, deterministic.
    """
    corroborating: list[str] = []
    contradicting: list[str] = []
    notes: list[str] = []

    for photo in photos:
        outcome = _classify_photo(photo, claim.change_type, spatial_buffer_m, temporal_window_days)
        if outcome == PhotoOutcome.CORROBORATES:
            corroborating.append(photo.photo_id)
        elif outcome == PhotoOutcome.CONTRADICTS:
            contradicting.append(photo.photo_id)

    # Determine overall outcome
    n_corr = len(corroborating)
    n_contra = len(contradicting)

    if n_corr == 0 and n_contra == 0:
        outcome_str = "UNVERIFIED"
        notes.append(
            "No DRISHTI photos found within the spatial/temporal window. "
            "Requires field verification."
        )
    elif n_contra > 0 and n_corr == 0:
        outcome_str = "FLAGGED_MISMATCH"
        notes.append(
            f"{n_contra} photo(s) contradict this satellite-claimed change. "
            "Flagged for field verification — do NOT auto-approve."
        )
    elif n_contra > 0 and n_corr > 0:
        outcome_str = "PARTIALLY_CORROBORATED"
        notes.append(
            f"{n_corr} corroborating photo(s) and {n_contra} contradicting photo(s). "
            "Partial evidence — review individual photos."
        )
    else:
        outcome_str = "PHOTO_CORROBORATED"

    return CrossValResult(
        claim_id=claim.claim_id,
        watershed_id=claim.watershed_id,
        epoch=claim.epoch,
        change_type=claim.change_type,
        outcome=outcome_str,
        corroborating_photo_ids=corroborating,
        contradicting_photo_ids=contradicting,
        notes=notes,
    )


def validate_watershed_epoch(
    watershed_id: str,
    epoch: str,
    claims: Sequence[SatelliteChangeClaim],
    photos: Sequence[PhotoRecord],
    spatial_buffer_m: float = 500.0,
    temporal_window_days: int = 90,
) -> WatershedCrossValSummary:
    """
    Cross-validate all satellite change claims for one watershed-epoch.
    Returns a summary with individual claim results and aggregate counts.
    Pure function.
    """
    results: list[CrossValResult] = []
    for claim in claims:
        result = validate_claim(claim, photos, spatial_buffer_m, temporal_window_days)
        results.append(result)

    counts = {"PHOTO_CORROBORATED": 0, "PARTIALLY_CORROBORATED": 0,
              "UNVERIFIED": 0, "FLAGGED_MISMATCH": 0}
    for r in results:
        counts[r.outcome] = counts.get(r.outcome, 0) + 1

    return WatershedCrossValSummary(
        watershed_id=watershed_id,
        epoch=epoch,
        total_claims=len(results),
        corroborated=counts["PHOTO_CORROBORATED"],
        partially_corroborated=counts["PARTIALLY_CORROBORATED"],
        unverified=counts["UNVERIFIED"],
        flagged_mismatches=counts["FLAGGED_MISMATCH"],
        results=results,
    )
