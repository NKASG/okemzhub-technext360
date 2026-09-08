from typing import Optional

from pydantic import BaseModel, ConfigDict


class BusinessRead(BaseModel):
    id: int
    slug: str
    name: str
    tagline: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
