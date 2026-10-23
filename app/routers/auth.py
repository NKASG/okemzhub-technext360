from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.dependencies import get_db
from app.models.login_log import LoginLog
from app.models.user import User
from app.schemas.token import Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Brute-force guard: after this many failed attempts on one username within the
# window, further attempts are refused until the window passes.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW = timedelta(minutes=15)


@router.post("/token", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT bearer token."""
    recent_failures = db.execute(
        select(func.count()).select_from(LoginLog).where(
            LoginLog.username_attempted == form_data.username,
            LoginLog.success.is_(False),
            LoginLog.timestamp >= datetime.now(timezone.utc) - LOCKOUT_WINDOW,
        )
    ).scalar_one()
    if recent_failures >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in 15 minutes.",
        )

    user = db.execute(
        select(User).where(User.username == form_data.username)
    ).scalar_one_or_none()

    ip = request.client.host if request.client else None
    success = bool(user and verify_password(form_data.password, user.hashed_password))

    db.add(LoginLog(
        user_id=user.id if user else None,
        username_attempted=form_data.username,
        success=success,
        ip_address=ip,
    ))
    db.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.username})
    return Token(access_token=token, token_type="bearer")
