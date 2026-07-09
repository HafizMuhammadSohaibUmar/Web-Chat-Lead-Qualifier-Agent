"""Lead model."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Lead(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: str
    business_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    service_type: str
    address: str
    urgency: str
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
