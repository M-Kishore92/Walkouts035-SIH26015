# DRISHTI-SRISHTI Intelligence Bridge (SIH 2026 — PS 26015)

> **Geospatial Watershed Intelligence Platform**  
> *Making field photos validate satellite claims — automatically.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-orange.svg)](https://postgis.net/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem (Grounded)

India's watershed development programs (**IWMP / WDC-PMKSY 2.0**) generate two independent data streams:

| Stream | Tool | Current Role |
|---|---|---|
| Geo-tagged field photos | **DRISHTI** (Android) | Decorative illustrations in PDF reports |
| Satellite LULC/NDVI/NDWI imagery | **SRISHTI** (Bhuvan Web-GIS) | Primary analysis layer |

These streams **never talk to each other**. Analysts manually paste DRISHTI photos into SRISHTI-derived PDF reports — one watershed at a time, one epoch at a time. The result: slow, inconsistent, unverifiable monitoring.

## The Solution

This platform builds an analytical bridge between DRISHTI and SRISHTI:

1. **Auto-classifies field photos** at capture (MobileNetV3, offline TFLite)
2. **Cross-validates** satellite-derived land/water change against photo evidence
3. **Flags mismatches** into a Field Verification Queue instead of silently entering reports
4. **Auto-generates** the structured IWMP monitoring report
5. **Scores every micro-watershed** with a single comparable **Watershed Impact Index (WII)**

The differentiator: satellite data and field photos become inputs **to each other**, not separate outputs shown side-by-side.

---

## Repository Structure

```
Walkouts035-SIH26015/
├── README.md
├── ARCHITECTURE.md          # System architecture decision records
├── RUNNING.md               # Verified runbook (demo-up in one command)
├── Makefile                 # Single-command workflow
├── docker-compose.yml       # Full stack (Postgres/PostGIS, Redis, MinIO, API, Workers)
│
├── backend/                 # FastAPI + Celery backend
│   ├── app/
│   │   ├── api/v1/          # REST endpoints
│   │   ├── core/            # Config, security, JWT auth
│   │   ├── db/              # SQLAlchemy + PostGIS session
│   │   ├── models/          # DB schema definitions
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/
│   │       ├── wii/         # ★ Pure-function Watershed Impact Index engine
│   │       ├── crossval/    # ★ Pure-function Cross-Validation engine
│   │       ├── satellite/   # Sentinel-2 / GEE NDVI/NDWI/LULC pipeline
│   │       ├── photo/       # CV auto-tagger + EXIF + pHash
│   │       ├── report/      # Auto-report generator (DOCX/PDF)
│   │       └── audit/       # Hash-chained adjudication ledger
│   ├── workers/             # Celery async workers
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                # React + Leaflet Web GIS Dashboard
│   ├── src/
│   │   ├── App.tsx
│   │   ├── screens/         # Map, Register, Verification, Analytics, Reports
│   │   ├── components/      # WII gauge, photo evidence, cross-val panel
│   │   └── styles/
│   ├── package.json
│   └── vite.config.ts
│
├── ml/                      # CV model training & inference
│   ├── classifier/          # MobileNetV3 structure classifier
│   │   ├── train.py
│   │   ├── infer.py
│   │   └── labels.py
│   └── models/              # Quantized TFLite model artifacts
│
├── db/                      # PostGIS schema + Alembic migrations
│   ├── alembic.ini
│   └── migrations/
│
├── tests/                   # 3-tier testing strategy
│   ├── unit/
│   │   ├── test_wii_purity.py        # AST: no IO in WII engine
│   │   └── test_crossval_purity.py   # AST: no IO in cross-val engine
│   ├── integration/
│   └── golden/
│       └── cases/*.yaml     # Declarative test scenarios
│
├── scripts/
│   ├── seed_demo.py         # Seeds Nanded/sample district data
│   ├── seed_users.py        # Seeds multi-role test users
│   ├── verify_endpoints.py  # Tests live govt/Sentinel API endpoints
│   ├── verify_ledger.py     # Verifies hash-chain integrity
│   └── vocabulary_lint.py   # Ethics vocabulary linter
│
└── docs/
    ├── adr/                 # Architecture Decision Records
    ├── api/                 # OpenAPI spec
    └── data-sources.md      # External data source audit
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/M-Kishore92/Walkouts035-SIH26015.git
cd Walkouts035-SIH26015

# 2. Spin up the full stack
make demo-up

# 3. Open the dashboard
open http://localhost:5173

# 4. Run the test suite
make test

# 5. Verify hash-chain ledger integrity
python scripts/verify_ledger.py
```

**Default demo credentials:**

| Role | Username | Password |
|---|---|---|
| Field Officer (WDT) | `officer.nanded` | `demo1234` |
| Monitoring (WCDC) | `monitor.nanded` | `demo1234` |
| State Planner (SLNA) | `planner.mh` | `demo1234` |
| Auditor (CAG) | `auditor.cag` | `demo1234` |

---

## Watershed Impact Index (WII)

```
WII = 0.30 × ΔNDVI_norm
    + 0.30 × ΔWaterSpread_norm
    + 0.25 × (1 − ΔDegradedLand_norm)
    + 0.15 × PhotoValidationConfidence
```

- All Δ terms are min-max normalized against district cohort for comparability
- `PhotoValidationConfidence` = share of satellite-claimed changes that are photo-corroborated
- **A watershed with impressive satellite NDVI gains but zero photo corroboration gets a lower WII** — preventing reward of unverifiable claims

---

## Core Design Principles

| Principle | Implementation |
|---|---|
| **Pure Functional Engines** | `wii.engine` and `crossval.engine` have zero IO, zero randomness, zero clock access |
| **AST Purity Tests** | CI fails if forbidden imports (`datetime`, `requests`, `random`) appear in engine modules |
| **Append-Only Ledger** | SQL `UPDATE`/`DELETE` revoked on `adjudication_ledger`; SHA-256 hash-chained |
| **No Accusatory Language** | `vocabulary_lint.py` bans judgmental vocabulary — strongest phrase is "requires field verification" |
| **Declarative Golden Cases** | 18 YAML scenarios covering all WII bands and cross-validation outcomes |
| **Single-Command Demo** | `make demo-up` seeds real satellite data and starts all services |

---

## Key Differentiators vs. Typical Hackathon Submissions

Most teams will display SRISHTI satellite layers and DRISHTI photos **on the same map** — that's digitizing the existing PDF report, not solving the problem.

This platform's core move:
1. **Photos validate satellite claims** (not just decorate them)
2. **Mismatches create a verification queue** (not a silent assumption)
3. **WII creates a comparable score** (not a narrative that varies analyst-to-analyst)
4. **Reports are auto-generated** in DoLR's exact format (not a new format no one will adopt)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.110+ (Python 3.11) |
| Task Queue | Celery 5 + Redis |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Object Storage | MinIO (S3-compatible) |
| Satellite Processing | GDAL 3.8, rasterio, GEE Python API |
| CV Model | TensorFlow Lite / ONNX Runtime (MobileNetV3) |
| Report Generation | python-docx + WeasyPrint |
| Frontend | React 18 + TypeScript + Leaflet + MapLibre GL |
| Containerization | Docker Compose v2 |

---

## License

MIT — see [LICENSE](LICENSE)

## Team

Built for Smart India Hackathon 2026, Problem Statement 26015  
*Department of Land Resources / Ministry of Rural Development*
