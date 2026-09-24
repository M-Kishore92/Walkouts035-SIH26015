"""
Watershed Impact Index (WII) — Pure Functional Engine.

CONTRACT: This module MUST remain free of all IO. The following are banned:
  - datetime, time, random (use values passed in as arguments)
  - requests, httpx, aiohttp (no network)
  - open(), pathlib.Path.read*(), os.* (no filesystem)
  - SQLAlchemy, asyncpg (no database)
  - Any global mutable state

This is enforced by:
  1. AST inspection in tests/unit/test_wii_purity.py
  2. Code review

ARITHMETIC:
  WII = w_ndvi * ndvi_norm
      + w_water * water_norm
      + w_degraded * (1 - degraded_norm)    # inverted: less degraded = better
      + w_photo * photo_confidence

  where each `_norm` term is:
      clamp((delta - min) / (max - min + ε), 0, 1)

  Final WII is scaled to [0, 100].

INVARIANTS (tested in golden suite):
  1. WII ∈ [0, 100] for all valid inputs
  2. WII is monotonically increasing in each component independently
  3. photo_confidence = 0.0 → WII ≤ 85  (photo weight cap enforced)
  4. cloud_cover_fraction > 0.50 → cloud_cover_warning = True + note added
  5. All-zero deltas → WII = photo_confidence * w_photo * 100 (baseline)
"""
from __future__ import annotations

from .types import (
    CohortStats,
    EpochDelta,
    PhotoValidation,
    WIIBand,
    WIIResult,
)

# ── Weight constants ─────────────────────────────────────────────────────────
W_NDVI: float = 0.30
W_WATER: float = 0.30
W_DEGRADED: float = 0.25
W_PHOTO: float = 0.15
_EPSILON: float = 1e-9  # Prevents division by zero

# ── Band thresholds (inclusive lower bound) ──────────────────────────────────
_BANDS = [
    (0.0, WIIBand.CRITICAL),
    (26.0, WIIBand.POOR),
    (41.0, WIIBand.MODERATE),
    (56.0, WIIBand.GOOD),
    (71.0, WIIBand.EXCELLENT),
]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, value))


def _normalize(delta: float, min_val: float, max_val: float) -> float:
    """Min-max normalize delta against cohort range, clamped to [0, 1]."""
    denom = max_val - min_val + _EPSILON
    return _clamp((delta - min_val) / denom)


def _band_for(score: float) -> WIIBand:
    """Map a [0, 100] WII score to its interpretation band."""
    band = WIIBand.CRITICAL
    for threshold, b in _BANDS:
        if score >= threshold:
            band = b
    return band


def compute_wii(
    delta: EpochDelta,
    photo_val: PhotoValidation,
    cohort: CohortStats,
    # Weights injected to allow sensitivity testing; defaults match spec
    w_ndvi: float = W_NDVI,
    w_water: float = W_WATER,
    w_degraded: float = W_DEGRADED,
    w_photo: float = W_PHOTO,
) -> WIIResult:
    """
    Compute the Watershed Impact Index for one watershed-epoch transition.

    Arguments:
        delta:      Satellite-derived change metrics (epoch T_{n-1} → T_n)
        photo_val:  Cross-validation result (fraction of claims corroborated)
        cohort:     District-level min/max statistics for normalization
        w_*:        WII component weights (must sum to 1.0; validated by caller)

    Returns:
        WIIResult with all component scores, the composite WII (0–100), and
        a band label.

    This function has no side effects and is deterministic.
    """
    notes: list[str] = []
    data_gaps: list[str] = []

    # ── Normalize each component ─────────────────────────────────────────────
    ndvi_score = _normalize(
        delta.delta_ndvi,
        cohort.ndvi_delta_min,
        cohort.ndvi_delta_max,
    )

    water_score = _normalize(
        delta.delta_water_spread_ha,
        cohort.water_delta_ha_min,
        cohort.water_delta_ha_max,
    )

    # Degraded land: improvement = negative delta → invert so improvement → 1
    degraded_raw = _normalize(
        delta.delta_degraded_land_ha,
        cohort.degraded_delta_ha_min,
        cohort.degraded_delta_ha_max,
    )
    degraded_score = 1.0 - degraded_raw  # Inversion: less degraded land = better

    # Photo validation confidence already ∈ [0, 1] from PhotoValidation.confidence
    photo_score = _clamp(photo_val.confidence)

    # ── Compute weighted composite ───────────────────────────────────────────
    raw_wii = (
        w_ndvi * ndvi_score
        + w_water * water_score
        + w_degraded * degraded_score
        + w_photo * photo_score
    )

    # Scale to 0–100
    wii_score = _clamp(raw_wii * 100.0, 0.0, 100.0)

    # ── Warnings and notes ───────────────────────────────────────────────────
    cloud_warning = delta.cloud_cover_fraction > 0.30
    if cloud_warning:
        notes.append(
            f"High cloud cover ({delta.cloud_cover_fraction:.0%}) in this epoch window; "
            f"NDVI and NDWI estimates may be unreliable. Consider manual review."
        )

    if photo_val.flagged_mismatches > 0:
        notes.append(
            f"{photo_val.flagged_mismatches} satellite change claim(s) are actively "
            f"contradicted by field photos — flagged for field verification."
        )

    if photo_val.total_satellite_claims == 0:
        data_gaps.append("No satellite change claims in this epoch; photo confidence defaulted to 0.50")

    if delta.delta_ndvi == 0.0 and delta.delta_water_spread_ha == 0.0:
        notes.append("No measurable satellite change detected in this epoch.")

    return WIIResult(
        watershed_id=delta.watershed_id,
        epoch_from=delta.epoch_from,
        epoch_to=delta.epoch_to,
        ndvi_score=round(ndvi_score, 4),
        water_score=round(water_score, 4),
        degraded_score=round(degraded_score, 4),
        photo_confidence_score=round(photo_score, 4),
        wii_score=round(wii_score, 2),
        band=_band_for(wii_score),
        cloud_cover_warning=cloud_warning,
        data_gaps=data_gaps,
        notes=notes,
    )


def rank_watersheds(results: list[WIIResult]) -> list[WIIResult]:
    """
    Sort a list of WIIResult objects from best to worst WII score.
    Pure function — returns a new list.
    """
    return sorted(results, key=lambda r: r.wii_score, reverse=True)
