from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_db, require_admin
from app.models.login_log import LoginLog
from app.models.user import User
from app.schemas.login_log import LoginLogRead

router = APIRouter(prefix="/login-logs", tags=["Login Logs"])


@router.get("/", response_model=list[LoginLogRead])
async def list_login_logs(
    limit: int = 300,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Return recent login attempts for your business, newest first.
    Failed attempts on unknown usernames (no linked user) are also included."""
    query = (
        select(LoginLog)
        .join(User, LoginLog.user_id == User.id, isouter=True)
        .options(selectinload(LoginLog.user))
        .where(
            or_(
                User.business_id == current_user.business_id,
                LoginLog.user_id.is_(None),
            )
        )
        .order_by(LoginLog.timestamp.desc())
        .limit(limit)
    )
    if user_id is not None:
        query = query.where(LoginLog.user_id == user_id)
    return db.execute(query).scalars().all()
