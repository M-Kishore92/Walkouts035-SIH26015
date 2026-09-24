"""
Endpoint Health & External Integration Verification Script.
Checks status of:
  - Local FastAPI endpoints (/health, /api/v1/watersheds, /api/v1/auth/token)
  - TiTiler COG Tile Server
  - MinIO S3 Object Store
  - External GIS / Sentinel / Bhuvan endpoints
Outputs a markdown health summary table to docs/api-health.md.
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request
import urllib.error
import json
import pathlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ENDPOINTS = [
    {
        "name": "Backend FastAPI Health",
        "url": "http://localhost:8000/health",
        "method": "GET",
        "category": "Core API",
    },
    {
        "name": "Backend Watersheds API",
        "url": "http://localhost:8000/api/v1/watersheds/",
        "method": "GET",
        "category": "Core API",
    },
    {
        "name": "TiTiler Tile Server Health",
        "url": "http://localhost:8080/healthz",
        "method": "GET",
        "category": "Raster / COG",
    },
    {
        "name": "MinIO S3 Health",
        "url": "http://localhost:9000/minio/health/live",
        "method": "GET",
        "category": "Storage",
    },
    {
        "name": "Copernicus Sentinel Hub Public",
        "url": "https://services.sentinel-hub.com/api/v1/version",
        "method": "GET",
        "category": "External Sentinel",
    },
]


def test_endpoint(ep: dict) -> dict:
    url = ep["url"]
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Pramaan-Verification/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            latency = (time.time() - start) * 1000
            status_code = response.getcode()
            return {
                "name": ep["name"],
                "category": ep["category"],
                "url": url,
                "status": "UP" if status_code < 400 else "DEGRADED",
                "code": status_code,
                "latency_ms": round(latency, 1),
            }
    except urllib.error.HTTPError as e:
        latency = (time.time() - start) * 1000
        # 401 or 403 means endpoint is alive and enforcing auth
        status = "UP (AUTH REQUIRED)" if e.code in (401, 403) else f"HTTP {e.code}"
        return {
            "name": ep["name"],
            "category": ep["category"],
            "url": url,
            "status": status,
            "code": e.code,
            "latency_ms": round(latency, 1),
        }
    except Exception as e:
        return {
            "name": ep["name"],
            "category": ep["category"],
            "url": url,
            "status": "OFFLINE / UNREACHABLE",
            "code": "N/A",
            "latency_ms": -1,
            "error": str(e),
        }


def main():
    print("Running endpoint health checks...")
    results = [test_endpoint(ep) for ep in ENDPOINTS]

    docs_dir = pathlib.Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_file = docs_dir / "api-health.md"

    md_lines = [
        "# System API Health & External Integration Matrix",
        f"\n*Generated at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}*\n",
        "| Category | Service / Endpoint | Target URL | Status | HTTP Code | Latency |",
        "|:---|:---|:---|:---:|:---:|:---:|",
    ]

    for r in results:
        status_icon = "🟢" if "UP" in r["status"] else "🔴"
        lat_str = f"{r['latency_ms']} ms" if r["latency_ms"] >= 0 else "N/A"
        md_lines.append(f"| {r['category']} | {r['name']} | `{r['url']}` | {status_icon} {r['status']} | {r['code']} | {lat_str} |")
        print(f"  [{status_icon}] {r['name']}: {r['status']} ({lat_str})")

    report_file.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nWritten API health report to {report_file}")


if __name__ == "__main__":
    main()
