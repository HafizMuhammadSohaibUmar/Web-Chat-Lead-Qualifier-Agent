"""Conversation phase helpers."""
from models.session import ChatPhase

REQUIRED_FIELDS = ("service_type", "address", "timeline", "urgency", "name")


def next_phase(lead_data: dict) -> ChatPhase:
    if not lead_data.get("service_type"):
        return ChatPhase.DISCOVERY
    if not (lead_data.get("address") and lead_data.get("timeline") and lead_data.get("urgency")):
        return ChatPhase.QUALIFICATION
    if not (lead_data.get("name") and (lead_data.get("phone") or lead_data.get("email"))):
        return ChatPhase.CONTACT
    return ChatPhase.CONFIRMATION


def qualification_complete(lead_data: dict) -> bool:
    return next_phase(lead_data) == ChatPhase.CONFIRMATION
