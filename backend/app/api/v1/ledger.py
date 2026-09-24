"""Ledger API — cryptographic audit trail for adjudication decisions."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.session import get_db
from app.models.models import AdjudicationEntry, SatelliteChangeClaim, User
from app.core.security import get_current_user, require_role
import hashlib, json
from datetime import datetime, timezone

router = APIRouter()


@router.post("/sign/{claim_id}")
async def sign_adjudication(
    claim_id: str, decision: str, notes: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("monitor", "admin")),
) -> dict:
    """Officer signs an adjudication decision — appends to hash-chained ledger."""
    if decision not in ("ACCEPT", "REJECT", "DEFER"):
        raise HTTPException(status_code=422, detail="decision must be ACCEPT, REJECT, or DEFER")

    claim = await db.scalar(select(SatelliteChangeClaim).where(SatelliteChangeClaim.id == claim_id))
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Get last ledger entry for chain
    last = await db.scalar(
        select(AdjudicationEntry).order_by(AdjudicationEntry.sequence_number.desc()).limit(1)
    )
    prev_hash = last.chain_hash if last else "0" * 64
    seq = (last.sequence_number + 1) if last else 1
    decided_at = datetime.now(timezone.utc)

    payload = json.dumps({
        "seq": seq, "claim_id": claim_id, "officer_id": str(current_user.id),
        "decision": decision, "decided_at": decided_at.isoformat(),
    }, sort_keys=True)

    payload_hash = hashlib.sha256(payload.encode()).hexdigest()
    chain_hash = hashlib.sha256(f"{payload_hash}{prev_hash}".encode()).hexdigest()

    entry = AdjudicationEntry(
        sequence_number=seq,
        claim_id=claim_id,
        officer_id=str(current_user.id),
        decision=decision,
        decision_notes=notes,
        decided_at=decided_at,
        payload_hash=payload_hash,
        previous_hash=prev_hash,
        chain_hash=chain_hash,
    )
    db.add(entry)
    await db.commit()
    return {"status": "signed", "sequence_number": seq, "chain_hash": chain_hash}


@router.get("/")
async def get_ledger(
    limit: int = 50, offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    entries = (await db.scalars(
        select(AdjudicationEntry).order_by(AdjudicationEntry.sequence_number.desc()).limit(limit).offset(offset)
    )).all()
    return {
        "entries": [
            {"sequence_number": e.sequence_number, "decision": e.decision,
             "decided_at": e.decided_at.isoformat(), "chain_hash": e.chain_hash,
             "previous_hash": e.previous_hash}
            for e in entries
        ]
    }


@router.get("/verify")
async def verify_chain(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Verify the entire hash chain is intact."""
    result = await db.execute(
        select(AdjudicationEntry).order_by(AdjudicationEntry.sequence_number)
    )
    entries = result.scalars().all()
    prev_hash = "0" * 64
    for e in entries:
        expected = hashlib.sha256(f"{e.payload_hash}{prev_hash}".encode()).hexdigest()
        if expected != e.chain_hash:
            return {"valid": False, "broken_at_sequence": e.sequence_number}
        prev_hash = e.chain_hash
    return {"valid": True, "total_entries": len(entries)}
