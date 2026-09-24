"""Auth API: token endpoint and user registration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import create_access_token, verify_password, hash_password
from app.db.session import get_db
from app.models.models import User

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Obtain a JWT access token."""
    user = await db.scalar(select(User).where(User.username == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token, role=user.role, username=user.username)


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)) -> dict:
    """Get current user profile (protected by Depends in middleware)."""
    return {"message": "Use with Authorization: Bearer <token>"}
