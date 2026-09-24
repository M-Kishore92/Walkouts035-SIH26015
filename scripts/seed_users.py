"""
Seed multi-role users for demo and testing.

Users seeded:
  - admin: admin@watershed.gov.in (role: admin)
  - monitor: monitor.nanded@watershed.gov.in (role: monitor, district: nanded)
  - officer: officer.degloor@watershed.gov.in (role: field_officer, district: nanded)
  - planner: planner.state@watershed.gov.in (role: planner, state: MH)
  - auditor: auditor.cag@gov.in (role: auditor)
"""
from __future__ import annotations

import asyncio
import sys
import uuid
import os

# Add backend to sys.path so app imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.models import User

TEST_USERS = [
    {
        "username": "admin",
        "email": "admin@watershed.gov.in",
        "password": "Password123!",
        "full_name": "System Administrator",
        "role": "admin",
        "district_code": "all",
        "state_code": "IN",
    },
    {
        "username": "monitor_nanded",
        "email": "monitor.nanded@watershed.gov.in",
        "password": "Password123!",
        "full_name": "Dr. Rajesh Kulkarni (District Monitoring Officer)",
        "role": "monitor",
        "district_code": "nanded",
        "state_code": "MH",
    },
    {
        "username": "officer_degloor",
        "email": "officer.degloor@watershed.gov.in",
        "password": "Password123!",
        "full_name": "Suresh Patil (WDT Field Officer)",
        "role": "field_officer",
        "district_code": "nanded",
        "state_code": "MH",
    },
    {
        "username": "planner_mh",
        "email": "planner.state@watershed.gov.in",
        "password": "Password123!",
        "full_name": "Pooja Shinde (State Watershed Directorate)",
        "role": "planner",
        "district_code": "all",
        "state_code": "MH",
    },
    {
        "username": "auditor_cag",
        "email": "auditor.cag@gov.in",
        "password": "Password123!",
        "full_name": "Anil Deshmukh (CAG Performance Auditor)",
        "role": "auditor",
        "district_code": "all",
        "state_code": "IN",
    },
]


async def seed_users() -> None:
    print(f"Connecting to database: {settings.DATABASE_URL} ...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for u in TEST_USERS:
            stmt = select(User).where(User.username == u["username"])
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                print(f"  [EXISTS] User '{u['username']}' already present.")
                continue

            user = User(
                id=str(uuid.uuid4()),
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                district_code=u["district_code"],
                state_code=u["state_code"],
                is_active=True,
            )
            session.add(user)
            print(f"  [CREATED] User '{u['username']}' ({u['role']}) created.")

        await session.commit()
    await engine.dispose()
    print("User seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_users())
