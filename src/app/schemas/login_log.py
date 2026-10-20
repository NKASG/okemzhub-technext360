from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead


class LoginLogRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    username_attempted: str
    success: bool
    ip_address: Optional[str] = None
    timestamp: datetime
    user: Optional[UserRead] = None
    model_config = ConfigDict(from_attributes=True)
