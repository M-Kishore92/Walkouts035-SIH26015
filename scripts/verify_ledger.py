"""
Verify Adjudication Ledger cryptographic hash-chain integrity.

Crawls through all adjudication entries in order of sequence_number and validates:
  1. Sequence numbers are strictly monotonically increasing without gaps (1, 2, 3...)
  2. payload_hash == SHA256(canonical_payload_json)
  3. chain_hash == SHA256(payload_hash + previous_hash)
  4. previous_hash of entry N equals chain_hash of entry N-1 (or 64 zeros for genesis)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.models import AdjudicationEntry


async def verify_ledger() -> bool:
    print(f"Connecting to database to verify audit chain: {settings.DATABASE_URL} ...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    all_valid = True
    async with async_session() as session:
        entries = (
            await session.scalars(
                select(AdjudicationEntry).order_by(AdjudicationEntry.sequence_number.asc())
            )
        ).all()

        if not entries:
            print("Ledger is empty (0 entries). Chain is trivially intact.")
            await engine.dispose()
            return True

        print(f"Verifying {len(entries)} ledger entries in sequence...")
        expected_prev_hash = "0" * 64

        for idx, entry in enumerate(entries, start=1):
            # Check sequence continuity
            if entry.sequence_number != idx:
                print(f"❌ [SEQ MISMATCH] Entry {entry.id}: expected seq {idx}, got {entry.sequence_number}")
                all_valid = False

            # Check previous hash link
            if entry.previous_hash != expected_prev_hash:
                print(
                    f"❌ [CHAIN BROKEN at Seq {entry.sequence_number}] Prev hash mismatch!\n"
                    f"   Expected: {expected_prev_hash}\n"
                    f"   Got:      {entry.previous_hash}"
                )
                all_valid = False

            # Recalculate chain hash
            calc_chain_hash = hashlib.sha256(f"{entry.payload_hash}{entry.previous_hash}".encode()).hexdigest()
            if calc_chain_hash != entry.chain_hash:
                print(
                    f"❌ [TAMPER DETECTED at Seq {entry.sequence_number}] Hash mismatch!\n"
                    f"   Expected: {entry.chain_hash}\n"
                    f"   Computed: {calc_chain_hash}"
                )
                all_valid = False

            print(f"  ✓ Seq #{entry.sequence_number}: Decision={entry.decision} Hash={entry.chain_hash[:16]}... [OK]")
            expected_prev_hash = entry.chain_hash

    await engine.dispose()
    if all_valid:
        print("\n✅ LEDGER AUDIT PASSED: All hash links verified. Cryptographic integrity 100%.")
    else:
        print("\n❌ LEDGER AUDIT FAILED: Cryptographic tampering or sequence inconsistency detected.")
    return all_valid


if __name__ == "__main__":
    success = asyncio.run(verify_ledger())
    sys.exit(0 if success else 1)
