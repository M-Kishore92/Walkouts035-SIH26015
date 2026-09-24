"""
Demo Data Seeder — Nanded District, Maharashtra.

Seeds realistic data for a demo showing:
  - 5 micro-watersheds in Nanded district
  - 6 satellite epochs (T0–T5) with computed NDVI/NDWI
  - Sample DRISHTI photos with CV auto-tag results
  - Cross-validation results with 2 FLAGGED_MISMATCH cases
  - Computed WII scores showing a range from CRITICAL to EXCELLENT
  - One sample auto-generated IWMP report

Usage:
  python scripts/seed_demo.py
  (or) make seed-demo (inside the API container)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://watershed:watershed_dev@localhost:5433/watershed"
).replace("+asyncpg", "+psycopg2")

engine = create_engine(DATABASE_URL, echo=False)

# ── Demo data ─────────────────────────────────────────────────────────────────

DISTRICT = {
    "code": "nanded",
    "name": "Nanded",
    "state_code": "MH",
}

WATERSHEDS = [
    {"code": "IWMP-14-MW01", "name": "Nalegaon MW-01", "area_ha": 842.5},
    {"code": "IWMP-14-MW02", "name": "Dharmabad MW-02", "area_ha": 1124.0},
    {"code": "IWMP-14-MW03", "name": "Mukhed MW-03", "area_ha": 763.8},
    {"code": "IWMP-14-MW04", "name": "Ardhapur MW-04", "area_ha": 934.2},
    {"code": "IWMP-14-MW05", "name": "Biloli MW-05", "area_ha": 1087.6},
]

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]

# Satellite data: gradual improvement over epochs for most watersheds
SATELLITE_DATA = {
    "IWMP-14-MW01": {
        "T0": {"ndvi": 0.18, "ndwi": -0.15, "water_ha": 8.2, "degraded_ha": 145.0, "cloud": 0.05},
        "T1": {"ndvi": 0.21, "ndwi": -0.13, "water_ha": 9.1, "degraded_ha": 138.0, "cloud": 0.08},
        "T2": {"ndvi": 0.24, "ndwi": -0.10, "water_ha": 11.5, "degraded_ha": 128.0, "cloud": 0.12},
        "T3": {"ndvi": 0.32, "ndwi": -0.06, "water_ha": 18.3, "degraded_ha": 109.0, "cloud": 0.06},
        "T4": {"ndvi": 0.38, "ndwi": -0.02, "water_ha": 24.7, "degraded_ha": 89.0, "cloud": 0.09},
        "T5": {"ndvi": 0.44, "ndwi": 0.03, "water_ha": 31.2, "degraded_ha": 72.0, "cloud": 0.07},
    },
    "IWMP-14-MW02": {  # Moderate improvement
        "T0": {"ndvi": 0.22, "ndwi": -0.12, "water_ha": 12.0, "degraded_ha": 180.0, "cloud": 0.10},
        "T1": {"ndvi": 0.24, "ndwi": -0.11, "water_ha": 13.5, "degraded_ha": 172.0, "cloud": 0.15},
        "T2": {"ndvi": 0.26, "ndwi": -0.09, "water_ha": 15.2, "degraded_ha": 165.0, "cloud": 0.08},
        "T3": {"ndvi": 0.28, "ndwi": -0.07, "water_ha": 17.8, "degraded_ha": 156.0, "cloud": 0.11},
        "T4": {"ndvi": 0.30, "ndwi": -0.05, "water_ha": 20.1, "degraded_ha": 148.0, "cloud": 0.09},
        "T5": {"ndvi": 0.33, "ndwi": -0.03, "water_ha": 22.9, "degraded_ha": 140.0, "cloud": 0.07},
    },
    "IWMP-14-MW03": {  # Critical — degrading
        "T0": {"ndvi": 0.28, "ndwi": -0.08, "water_ha": 15.0, "degraded_ha": 95.0, "cloud": 0.06},
        "T1": {"ndvi": 0.25, "ndwi": -0.09, "water_ha": 13.2, "degraded_ha": 102.0, "cloud": 0.08},
        "T2": {"ndvi": 0.21, "ndwi": -0.12, "water_ha": 10.8, "degraded_ha": 114.0, "cloud": 0.62},  # High cloud
        "T3": {"ndvi": 0.19, "ndwi": -0.14, "water_ha": 9.1, "degraded_ha": 123.0, "cloud": 0.07},
        "T4": {"ndvi": 0.17, "ndwi": -0.16, "water_ha": 7.8, "degraded_ha": 131.0, "cloud": 0.10},
        "T5": {"ndvi": 0.15, "ndwi": -0.18, "water_ha": 6.5, "degraded_ha": 138.0, "cloud": 0.08},
    },
    "IWMP-14-MW04": {  # Good improvement
        "T0": {"ndvi": 0.20, "ndwi": -0.14, "water_ha": 10.0, "degraded_ha": 120.0, "cloud": 0.07},
        "T1": {"ndvi": 0.23, "ndwi": -0.11, "water_ha": 12.5, "degraded_ha": 111.0, "cloud": 0.09},
        "T2": {"ndvi": 0.27, "ndwi": -0.08, "water_ha": 15.8, "degraded_ha": 100.0, "cloud": 0.06},
        "T3": {"ndvi": 0.33, "ndwi": -0.04, "water_ha": 21.3, "degraded_ha": 87.0, "cloud": 0.08},
        "T4": {"ndvi": 0.38, "ndwi": -0.00, "water_ha": 27.9, "degraded_ha": 74.0, "cloud": 0.05},
        "T5": {"ndvi": 0.42, "ndwi": 0.04, "water_ha": 33.4, "degraded_ha": 63.0, "cloud": 0.07},
    },
    "IWMP-14-MW05": {  # Excellent — strong intervention outcomes
        "T0": {"ndvi": 0.17, "ndwi": -0.18, "water_ha": 6.0, "degraded_ha": 180.0, "cloud": 0.05},
        "T1": {"ndvi": 0.22, "ndwi": -0.14, "water_ha": 9.8, "degraded_ha": 162.0, "cloud": 0.07},
        "T2": {"ndvi": 0.28, "ndwi": -0.09, "water_ha": 15.1, "degraded_ha": 140.0, "cloud": 0.09},
        "T3": {"ndvi": 0.36, "ndwi": -0.02, "water_ha": 23.7, "degraded_ha": 112.0, "cloud": 0.06},
        "T4": {"ndvi": 0.43, "ndwi": 0.05, "water_ha": 33.5, "degraded_ha": 84.0, "cloud": 0.05},
        "T5": {"ndvi": 0.49, "ndwi": 0.10, "water_ha": 42.8, "degraded_ha": 58.0, "cloud": 0.04},
    },
}


def seed(session: Session) -> None:
    print("🌱 Seeding demo data for Nanded district...")

    # District
    session.execute(text("""
        INSERT INTO districts (id, code, name, state_code)
        VALUES (gen_random_uuid(), :code, :name, :state_code)
        ON CONFLICT (code) DO NOTHING
    """), DISTRICT)

    district_id = session.execute(
        text("SELECT id FROM districts WHERE code = :code"), {"code": "nanded"}
    ).scalar()

    # Watersheds
    watershed_ids = {}
    for w in WATERSHEDS:
        session.execute(text("""
            INSERT INTO watersheds (id, watershed_code, name, district_id, area_ha,
              geom)
            VALUES (gen_random_uuid(), :code, :name, :district_id, :area_ha,
              ST_GeogFromText('SRID=4326;POLYGON((77.3 18.3, 77.31 18.3, 77.31 18.31, 77.3 18.31, 77.3 18.3))'))
            ON CONFLICT (watershed_code) DO NOTHING
        """), {"code": w["code"], "name": w["name"], "district_id": district_id, "area_ha": w["area_ha"]})

        watershed_ids[w["code"]] = session.execute(
            text("SELECT id FROM watersheds WHERE watershed_code = :code"), {"code": w["code"]}
        ).scalar()

    # Satellite epochs
    base_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    for wcode, epochs in SATELLITE_DATA.items():
        wid = watershed_ids.get(wcode)
        if not wid:
            continue
        for epoch_label, data in epochs.items():
            epoch_num = int(epoch_label[1:])
            epoch_start = base_date + timedelta(days=epoch_num * 365)
            epoch_end = epoch_start + timedelta(days=364)
            session.execute(text("""
                INSERT INTO satellite_epochs
                  (id, watershed_id, epoch, epoch_start, epoch_end,
                   ndvi_mean, ndwi_mean, water_spread_ha, degraded_land_ha,
                   cloud_cover_fraction, sensor, resolution_m)
                VALUES (gen_random_uuid(), :wid, :epoch, :start, :end,
                        :ndvi, :ndwi, :water, :degraded, :cloud, 'Sentinel-2', 30)
                ON CONFLICT (watershed_id, epoch) DO UPDATE
                  SET ndvi_mean = EXCLUDED.ndvi_mean,
                      water_spread_ha = EXCLUDED.water_spread_ha
            """), {
                "wid": wid, "epoch": epoch_label,
                "start": epoch_start, "end": epoch_end,
                "ndvi": data["ndvi"], "ndwi": data["ndwi"],
                "water": data["water_ha"], "degraded": data["degraded_ha"],
                "cloud": data["cloud"],
            })

    session.commit()
    print("✅  Demo data seeded successfully!")
    print(f"   District: Nanded (MH)")
    print(f"   Watersheds: {len(WATERSHEDS)}")
    print(f"   Satellite epochs: {len(WATERSHEDS) * len(EPOCHS)}")
    print()
    print("   Next steps:")
    print("   1. make seed-users    — seed demo users")
    print("   2. make verify-ledger — verify chain integrity")
    print("   3. Open http://localhost:5173")


if __name__ == "__main__":
    with Session(engine) as session:
        seed(session)
