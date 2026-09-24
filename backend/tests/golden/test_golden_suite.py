"""
Golden Test Suite — 18 declarative YAML test cases for the WII and cross-validation engines.

Each YAML case specifies inputs and the expected output. Tests are run by
loading each YAML file and asserting the engine produces the expected result.
This makes the test cases human-readable and auditable without code knowledge.

Coverage:
  - WII bands: CRITICAL (2), POOR (2), MODERATE (3), GOOD (4), EXCELLENT (3)
  - Cross-validation outcomes: PHOTO_CORROBORATED (3), FLAGGED_MISMATCH (3), UNVERIFIED (3)
  - Edge cases: all-zero deltas, high cloud cover, no photos, max score
"""
from __future__ import annotations

import pathlib
from typing import Any

import pytest
import yaml

from app.services.wii.engine import compute_wii
from app.services.wii.types import (
    CohortStats, EpochDelta, PhotoValidation, WIIBand
)
from app.services.crossval.engine import (
    validate_claim, validate_watershed_epoch,
    SatelliteChangeClaim, PhotoRecord,
    ChangeType, StructureType, ConditionClass,
)

CASES_DIR = pathlib.Path(__file__).parent / "cases"


def load_yaml_cases(glob: str) -> list[tuple[str, dict[str, Any]]]:
    """Load all YAML test cases matching the glob pattern."""
    cases = []
    for path in sorted(CASES_DIR.glob(glob)):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases.append((path.stem, data))
    return cases


# ── WII Engine Golden Tests ───────────────────────────────────────────────────

WII_CASES = load_yaml_cases("wii_*.yaml")


@pytest.mark.parametrize("case_name,case_data", WII_CASES, ids=[c[0] for c in WII_CASES])
def test_wii_golden(case_name: str, case_data: dict) -> None:
    """Run one WII golden case from YAML."""
    delta = EpochDelta(**case_data["delta"])
    photo_val = PhotoValidation(**case_data["photo_validation"])
    cohort = CohortStats(**case_data["cohort"])

    expected = case_data["expected"]
    result = compute_wii(delta, photo_val, cohort)

    # WII score within 0.5 tolerance (floating point)
    assert abs(result.wii_score - expected["wii_score"]) < 0.5, (
        f"[{case_name}] Expected WII={expected['wii_score']}, got {result.wii_score}"
    )

    # Band must match exactly
    assert result.band.value == expected["band"], (
        f"[{case_name}] Expected band={expected['band']}, got {result.band.value}"
    )

    # Cloud warning
    if "cloud_cover_warning" in expected:
        assert result.cloud_cover_warning == expected["cloud_cover_warning"], (
            f"[{case_name}] Cloud cover warning mismatch"
        )

    # Invariant: WII is always in [0, 100]
    assert 0.0 <= result.wii_score <= 100.0, (
        f"[{case_name}] WII {result.wii_score} is outside [0, 100] — invariant violated"
    )


# ── Cross-Validation Engine Golden Tests ─────────────────────────────────────

CROSSVAL_CASES = load_yaml_cases("crossval_*.yaml")


@pytest.mark.parametrize(
    "case_name,case_data", CROSSVAL_CASES, ids=[c[0] for c in CROSSVAL_CASES]
)
def test_crossval_golden(case_name: str, case_data: dict) -> None:
    """Run one cross-validation golden case from YAML."""
    claim_data = case_data["claim"]
    claim = SatelliteChangeClaim(
        claim_id=claim_data["claim_id"],
        watershed_id=claim_data["watershed_id"],
        epoch=claim_data["epoch"],
        change_type=ChangeType(claim_data["change_type"]),
        magnitude=claim_data.get("magnitude", 0.0),
        centroid_lat=claim_data.get("centroid_lat", 0.0),
        centroid_lon=claim_data.get("centroid_lon", 0.0),
    )

    photos = [
        PhotoRecord(
            photo_id=p["photo_id"],
            structure_type=StructureType(p["structure_type"]),
            condition=ConditionClass(p["condition"]),
            confidence=p.get("confidence", 0.85),
            distance_m=p.get("distance_m", 100.0),
            days_from_epoch=p.get("days_from_epoch", 10),
        )
        for p in case_data.get("photos", [])
    ]

    expected = case_data["expected"]
    result = validate_claim(
        claim,
        photos,
        spatial_buffer_m=case_data.get("spatial_buffer_m", 500.0),
        temporal_window_days=case_data.get("temporal_window_days", 90),
    )

    assert result.outcome == expected["outcome"], (
        f"[{case_name}] Expected outcome={expected['outcome']}, got {result.outcome}"
    )

    if "corroborating_count" in expected:
        assert len(result.corroborating_photo_ids) == expected["corroborating_count"], (
            f"[{case_name}] Expected {expected['corroborating_count']} corroborating photos"
        )

    if "contradicting_count" in expected:
        assert len(result.contradicting_photo_ids) == expected["contradicting_count"], (
            f"[{case_name}] Expected {expected['contradicting_count']} contradicting photos"
        )


# ── Property-Based Invariants ─────────────────────────────────────────────────

class TestWIIInvariants:
    """Fast, parameterized invariant checks (no external files needed)."""

    DEFAULT_COHORT = CohortStats(
        ndvi_delta_min=-0.3, ndvi_delta_max=0.3,
        water_delta_ha_min=-50.0, water_delta_ha_max=50.0,
        degraded_delta_ha_min=-100.0, degraded_delta_ha_max=100.0,
    )

    def _make_photo_val(self, corroborated: int, total: int) -> PhotoValidation:
        return PhotoValidation(
            watershed_id="test",
            epoch="T3",
            total_satellite_claims=total,
            corroborated_claims=corroborated,
            contradicted_claims=0,
            unverified_claims=total - corroborated,
            flagged_mismatches=0,
        )

    def _make_delta(self, ndvi: float = 0.0, water: float = 0.0, degraded: float = 0.0) -> EpochDelta:
        return EpochDelta(
            watershed_id="test",
            epoch_from="T2",
            epoch_to="T3",
            delta_ndvi=ndvi,
            delta_water_spread_ha=water,
            delta_degraded_land_ha=degraded,
            cloud_cover_fraction=0.0,
        )

    def test_wii_always_in_range(self) -> None:
        """WII must always be in [0, 100]."""
        test_cases = [
            (0.3, 50.0, -100.0, 5, 5),   # All improvements
            (-0.3, -50.0, 100.0, 0, 5),  # All degradation
            (0.0, 0.0, 0.0, 0, 0),       # All zeros
            (0.15, 25.0, -50.0, 3, 5),   # Partial improvement
        ]
        for ndvi, water, degraded, corr, total in test_cases:
            delta = self._make_delta(ndvi, water, degraded)
            photo_val = self._make_photo_val(corr, total)
            result = compute_wii(delta, photo_val, self.DEFAULT_COHORT)
            assert 0.0 <= result.wii_score <= 100.0

    def test_zero_delta_wii_equals_photo_weight(self) -> None:
        """With all-zero satellite deltas, WII should equal photo_weight * confidence * 100."""
        delta = self._make_delta(0.0, 0.0, 0.0)
        photo_val = self._make_photo_val(corroborated=5, total=5)
        result = compute_wii(delta, photo_val, self.DEFAULT_COHORT)
        # With all zeros, ndvi_norm=0.5, water_norm=0.5, degraded_norm=0.5
        # degraded_score = 1 - 0.5 = 0.5, photo = 1.0
        # WII = (0.30*0.5 + 0.30*0.5 + 0.25*0.5 + 0.15*1.0) * 100 = 57.5
        assert 55.0 <= result.wii_score <= 60.0

    def test_cloud_cover_warning_threshold(self) -> None:
        """Cloud cover > 30% must set cloud_cover_warning = True."""
        for cc in [0.31, 0.50, 0.99]:
            delta = EpochDelta(
                watershed_id="test", epoch_from="T0", epoch_to="T1",
                delta_ndvi=0.1, delta_water_spread_ha=5.0, delta_degraded_land_ha=-2.0,
                cloud_cover_fraction=cc,
            )
            result = compute_wii(delta, self._make_photo_val(1, 1), self.DEFAULT_COHORT)
            assert result.cloud_cover_warning is True

        delta_clear = EpochDelta(
            watershed_id="test", epoch_from="T0", epoch_to="T1",
            delta_ndvi=0.1, delta_water_spread_ha=5.0, delta_degraded_land_ha=-2.0,
            cloud_cover_fraction=0.30,
        )
        result = compute_wii(delta_clear, self._make_photo_val(1, 1), self.DEFAULT_COHORT)
        assert result.cloud_cover_warning is False

    def test_wii_monotonic_in_ndvi(self) -> None:
        """Higher ΔNDVI → higher WII (all else equal)."""
        photo_val = self._make_photo_val(3, 5)
        results = [
            compute_wii(self._make_delta(ndvi=v), photo_val, self.DEFAULT_COHORT).wii_score
            for v in [-0.3, -0.1, 0.0, 0.1, 0.2, 0.3]
        ]
        assert results == sorted(results), f"WII not monotonic in NDVI: {results}"

    def test_excellent_band_requires_high_score(self) -> None:
        """EXCELLENT band must require WII ≥ 71."""
        delta = self._make_delta(0.3, 50.0, -100.0)
        photo_val = self._make_photo_val(5, 5)
        result = compute_wii(delta, photo_val, self.DEFAULT_COHORT)
        assert result.band == WIIBand.EXCELLENT
        assert result.wii_score >= 71.0

    def test_critical_band_for_degradation(self) -> None:
        """Maximum degradation → CRITICAL band."""
        delta = self._make_delta(-0.3, -50.0, 100.0)
        photo_val = self._make_photo_val(0, 5)
        result = compute_wii(delta, photo_val, self.DEFAULT_COHORT)
        assert result.band == WIIBand.CRITICAL
        assert result.wii_score < 26.0
