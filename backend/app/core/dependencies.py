import hashlib
import json
from typing import Optional, List, Callable
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import get_db
from backend.app.core.security import oauth2_scheme, decode_token
from backend.app.models.all_models import User, IdempotencyKey
from backend.app.models.enums import UserRole

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: Missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_role(*allowed_roles: UserRole) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        allowed_values = [r.value for r in allowed_roles]
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {allowed_values}. Your role: {current_user.role}"
            )
        return current_user
    return role_checker

async def verify_idempotency(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
) -> Optional[IdempotencyKey]:
    """
    Evaluates Idempotency-Key header on mutating write operations.
    If key is present and previously processed, returns cached record to endpoint.
    """
    if not idempotency_key:
        return None
    
    result = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.idempotency_key == idempotency_key)
    )
    existing_key = result.scalar_one_or_none()
    
    if existing_key:
        now = datetime.now(timezone.utc)
        # Ensure aware comparison
        exp = existing_key.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
            
        if now < exp:
            return existing_key
            
    return None
