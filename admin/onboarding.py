"""Admin onboarding endpoint helpers."""
from pydantic import BaseModel, Field

from rag.knowledge_loader import onboard_knowledge_base


class KnowledgePayload(BaseModel):
    business_name: str
    business_type: str
    service_area_cities: list[str] = Field(default_factory=list)
    services_offered: list[str] = Field(default_factory=list)
    faqs: list[dict | str] = Field(default_factory=list)
    business_hours: str = ""
    emergency_availability: str = ""
    special_notes: str = ""


async def onboard_business(business_id: str, payload: KnowledgePayload) -> dict:
    return await onboard_knowledge_base(business_id, payload.model_dump())
