"""Admin API — user management and district administration."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import User, District
from app.core.security import hash_password, require_role

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str
    district_code: str | None = None
    state_code: str | None = None


@router.post("/users", status_code=201)
async def create_user(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> dict:
    existing = await db.scalar(select(User).where(User.username == req.username))
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=req.username, email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name, role=req.role,
        district_code=req.district_code, state_code=req.state_code,
    )
    db.add(user)
    await db.commit()
    return {"id": str(user.id), "username": user.username, "role": user.role}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> dict:
    users = (await db.scalars(select(User).limit(200))).all()
    return {
        "users": [
            {"id": str(u.id), "username": u.username, "role": u.role,
             "district_code": u.district_code, "is_active": u.is_active}
            for u in users
        ]
    }
