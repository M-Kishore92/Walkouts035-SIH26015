"""
Satellite Processing Pipeline — Sentinel-2 / Google Earth Engine.

Responsibilities:
  1. Fetch Cloud-Optimized GeoTIFFs (COGs) from GEE or Sentinel Hub
  2. Compute NDVI, NDWI per watershed polygon per epoch
  3. Run LULC classification (Random Forest)
  4. Detect and flag satellite change claims (WATER_INCREASE, VEGETATION_INCREASE, etc.)
  5. Store raster layers as COGs in MinIO for the TiTiler tile server

Design: Each function is idempotent — safe to re-run without duplication.
GEE API is optional; falls back to synthetic data for offline demo.
"""
from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# Thresholds for change detection
WATER_INCREASE_THRESHOLD_HA = 1.0    # Min detectable water body increase
VEGETATION_INCREASE_THRESHOLD = 0.05  # Min NDVI delta to flag
DEGRADED_REDUCTION_THRESHOLD_HA = 1.0


@dataclass
class EpochResult:
    """Satellite processing result for one watershed-epoch."""
    watershed_id: str
    epoch: str
    ndvi_mean: float
    ndwi_mean: float
    water_spread_ha: float
    degraded_land_ha: float
    vegetation_ha: float
    agriculture_ha: float
    cloud_cover_fraction: float
    lulc_classes: dict
    ndvi_cog_key: Optional[str] = None
    ndwi_cog_key: Optional[str] = None
    lulc_cog_key: Optional[str] = None


def compute_ndvi(nir_band: np.ndarray, red_band: np.ndarray) -> np.ndarray:
    """
    Compute Normalized Difference Vegetation Index.
    NDVI = (NIR - Red) / (NIR + Red + ε)
    Pure numpy computation, deterministic.
    """
    epsilon = 1e-9
    nir = nir_band.astype(np.float32)
    red = red_band.astype(np.float32)
    return (nir - red) / (nir + red + epsilon)


def compute_ndwi(green_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
    """
    Compute Normalized Difference Water Index (McFeeters 1996).
    NDWI = (Green - NIR) / (Green + NIR + ε)
    Positive NDWI → water bodies.
    """
    epsilon = 1e-9
    green = green_band.astype(np.float32)
    nir = nir_band.astype(np.float32)
    return (green - nir) / (green + nir + epsilon)


def mask_clouds(qa_band: np.ndarray) -> np.ndarray:
    """
    Create a boolean cloud mask from Sentinel-2 Scene Classification Layer (SCL).
    SCL values 8 (medium prob cloud), 9 (high prob cloud), 10 (thin cirrus), 11 (snow) = cloudy.
    Returns True where pixel is valid (not cloud).
    """
    cloud_values = {8, 9, 10, 11}
    mask = np.ones_like(qa_band, dtype=bool)
    for val in cloud_values:
        mask &= (qa_band != val)
    return mask


def classify_lulc_rf(ndvi: np.ndarray, ndwi: np.ndarray) -> np.ndarray:
    """
    Simple rule-based LULC classification (proxy for Random Forest in production).
    Classes:
      0 = water (NDWI > 0.1)
      1 = vegetation (NDVI > 0.4)
      2 = agriculture (0.2 < NDVI ≤ 0.4)
      3 = degraded/barren (NDVI ≤ 0.2 and NDWI ≤ 0.1)
    In production, replace with trained sklearn RandomForestClassifier.
    """
    lulc = np.full(ndvi.shape, 3, dtype=np.uint8)  # Default: degraded
    lulc[ndvi > 0.2] = 2   # Agriculture
    lulc[ndvi > 0.4] = 1   # Vegetation
    lulc[ndwi > 0.1] = 0   # Water
    return lulc


def pixel_area_to_ha(pixel_count: int, resolution_m: int = 30) -> float:
    """Convert pixel count to hectares at the given resolution."""
    return pixel_count * (resolution_m ** 2) / 10000.0


def detect_change_claims(
    epoch_from: EpochResult,
    epoch_to: EpochResult,
) -> list[dict]:
    """
    Compare two epochs and generate satellite change claims requiring photo corroboration.
    Returns a list of claim dicts (serializable).
    """
    claims = []

    # Water increase
    water_delta = epoch_to.water_spread_ha - epoch_from.water_spread_ha
    if water_delta >= WATER_INCREASE_THRESHOLD_HA:
        claims.append({
            "change_type": "WATER_INCREASE",
            "magnitude": round(water_delta, 2),
            "description": f"Water body area increased by {water_delta:.1f} ha",
        })

    # Vegetation increase
    ndvi_delta = epoch_to.ndvi_mean - epoch_from.ndvi_mean
    if ndvi_delta >= VEGETATION_INCREASE_THRESHOLD:
        claims.append({
            "change_type": "VEGETATION_INCREASE",
            "magnitude": round(ndvi_delta, 4),
            "description": f"Mean NDVI increased by {ndvi_delta:.3f}",
        })

    # Degraded land reduction
    degraded_delta = epoch_from.degraded_land_ha - epoch_to.degraded_land_ha
    if degraded_delta >= DEGRADED_REDUCTION_THRESHOLD_HA:
        claims.append({
            "change_type": "DEGRADED_REDUCTION",
            "magnitude": round(degraded_delta, 2),
            "description": f"Degraded land reduced by {degraded_delta:.1f} ha",
        })

    return claims


def compute_satellite_epoch(watershed_id: str, epoch: str) -> dict:
    """
    Compute satellite metrics for one watershed-epoch.
    In production: calls GEE Python API to fetch Sentinel-2 composites.
    For offline demo: generates realistic synthetic data based on a
    seeded pseudo-random process anchored to watershed_id + epoch.
    """
    try:
        return _compute_via_gee(watershed_id, epoch)
    except Exception as e:
        log.warning(f"GEE unavailable ({e}), using synthetic satellite data")
        return _compute_synthetic(watershed_id, epoch)


def _compute_via_gee(watershed_id: str, epoch: str) -> dict:
    """Fetch real Sentinel-2 imagery via Google Earth Engine."""
    try:
        import ee  # type: ignore[import]
    except ImportError:
        raise RuntimeError("earthengine-api not installed")

    # GEE initialization should happen at app startup
    # For now raise to fall through to synthetic
    raise RuntimeError("GEE not configured")


def _compute_synthetic(watershed_id: str, epoch: str) -> dict:
    """
    Generate realistic synthetic satellite data for offline demo.
    Seed is anchored to watershed_id + epoch for determinism.
    """
    import hashlib
    seed_bytes = hashlib.md5(f"{watershed_id}-{epoch}".encode()).hexdigest()
    seed = int(seed_bytes[:8], 16)
    rng = np.random.default_rng(seed)

    epoch_num = int(epoch[1:]) if epoch[1:].isdigit() else 0

    # Simulate gradual improvement over epochs (typical post-intervention trajectory)
    base_ndvi = 0.22 + epoch_num * 0.04 + rng.normal(0, 0.02)
    base_ndwi = -0.10 + epoch_num * 0.01 + rng.normal(0, 0.01)
    water_ha = 8.0 + epoch_num * 3.5 + rng.normal(0, 1.5)
    degraded_ha = 120.0 - epoch_num * 15.0 + rng.normal(0, 5.0)
    cloud_cover = float(rng.uniform(0.02, 0.15))

    result = EpochResult(
        watershed_id=watershed_id,
        epoch=epoch,
        ndvi_mean=float(np.clip(base_ndvi, -1, 1)),
        ndwi_mean=float(np.clip(base_ndwi, -1, 1)),
        water_spread_ha=float(max(0, water_ha)),
        degraded_land_ha=float(max(0, degraded_ha)),
        vegetation_ha=float(max(0, 200 + epoch_num * 12 + rng.normal(0, 8))),
        agriculture_ha=float(max(0, 350 + epoch_num * 5 + rng.normal(0, 10))),
        cloud_cover_fraction=cloud_cover,
        lulc_classes={
            "water": float(max(0, water_ha)),
            "vegetation": float(max(0, 200 + epoch_num * 12)),
            "agriculture": float(max(0, 350 + epoch_num * 5)),
            "degraded": float(max(0, degraded_ha)),
        },
    )

    return {
        "watershed_id": watershed_id,
        "epoch": epoch,
        "ndvi_mean": result.ndvi_mean,
        "ndwi_mean": result.ndwi_mean,
        "water_spread_ha": result.water_spread_ha,
        "degraded_land_ha": result.degraded_land_ha,
        "vegetation_ha": result.vegetation_ha,
        "agriculture_ha": result.agriculture_ha,
        "cloud_cover_fraction": result.cloud_cover_fraction,
        "lulc_classes": result.lulc_classes,
        "sensor": "Sentinel-2 (synthetic)",
        "resolution_m": 30,
    }
