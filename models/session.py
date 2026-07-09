"""Chat session models."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChatPhase(str, Enum):
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    CONTACT = "contact"
    CONFIRMATION = "confirmation"


class Message(BaseModel):
    role: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    business_id: str
    session_token: str
    messages: list[Message] = Field(default_factory=list)
    phase: ChatPhase = ChatPhase.DISCOVERY
    lead_extracted: bool = False
    lead_data: dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    token: str
    message: str
    business_id: Optional[str] = None
