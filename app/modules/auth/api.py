from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.auth.schemas import LoginRequest, SignupRequest, TokenResponse, UserMeResponse
from app.modules.auth.service import create_access_token, verify_password
from app.modules.users.models import User
from app.modules.users.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(User).where(User.email == data.email))
    if r.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    svc = UserService(db)
    user = await svc.create_with_password(email=data.email, password=data.password)
    token = create_access_token({"sub": user.user_id, "email": user.email})
    return TokenResponse(access_token=token, user_id=user.user_id)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(User).where(User.email == data.email))
    user = r.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token({"sub": user.user_id, "email": user.email})
    return TokenResponse(access_token=token, user_id=user.user_id)


@router.get("/me", response_model=UserMeResponse)
async def me(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(User).where(User.user_id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return UserMeResponse(user_id=user.user_id, email=user.email)
