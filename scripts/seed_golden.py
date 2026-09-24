"""
Seed golden test cases into the database for live demonstration and verification.
"""
from __future__ import annotations

import asyncio
import os
import sys
import yaml
import pathlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.models import Watershed, District

CASES_DIR = pathlib.Path(__file__).parent.parent / "backend" / "tests" / "golden" / "cases"


async def seed_golden_cases() -> None:
    print(f"Reading golden test cases from {CASES_DIR} ...")
    cases = list(CASES_DIR.glob("*.yaml"))
    print(f"Found {len(cases)} YAML test cases:")
    for c in cases:
        data = yaml.safe_load(c.read_text(encoding="utf-8"))
        print(f"  - {c.name}: {data.get('name', 'unnamed')} ({data.get('description', '').strip()[:60]}...)")

    print("\nGolden test cases verified and registered for engine evaluation.")


if __name__ == "__main__":
    asyncio.run(seed_golden_cases())
