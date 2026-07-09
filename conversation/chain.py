"""Conversation chain and lead qualification."""
import re
from datetime import datetime, timezone

from config import get_settings
from conversation.phases import next_phase, qualification_complete
from conversation.prompts import build_system_prompt
from integrations.llm_client import complete_chat
from integrations.supabase_client import supabase_client
from integrations.twilio_client import twilio_client
from models.lead import Lead
from models.session import ChatPhase, Message
from rag.retriever import retrieve_context
from security import detect_prompt_injection, sanitize_user_input

PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")


def extract_lead_fields(text: str, existing: dict | None = None) -> dict:
    data = dict(existing or {})
    lowered = text.lower()
    service_keywords = {
        "hvac": ("hvac", "ac", "air conditioner", "furnace", "heating"),
        "plumbing": ("plumb", "leak", "drain", "water heater", "toilet"),
        "roofing": ("roof", "shingle", "gutter"),
        "pest control": ("pest", "termite", "ant", "bug", "rodent"),
        "electrical": ("electric", "breaker", "outlet", "light"),
    }
    for service, words in service_keywords.items():
        if any(word in lowered for word in words):
            data.setdefault("service_type", service)
    if "today" in lowered or "now" in lowered or "emergency" in lowered or "urgent" in lowered:
        data["timeline"] = "today"
        data["urgency"] = "high"
    elif "this week" in lowered or "tomorrow" in lowered:
        data.setdefault("timeline", "this week")
        data.setdefault("urgency", "medium")
    elif "soon" in lowered:
        data.setdefault("timeline", "soon")
        data.setdefault("urgency", "medium")
    data.setdefault("urgency", "normal")
    phone = PHONE_RE.search(text)
    if phone:
        data["phone"] = phone.group(1).strip()
    email = EMAIL_RE.search(text)
    if email:
        data["email"] = email.group(0)
    zip_code = ZIP_RE.search(text)
    if zip_code:
        data.setdefault("address", zip_code.group(0))
    address_match = re.search(
        r"\b(?:at|address is|near)\s+([A-Za-z0-9 .#-]{6,80}?)(?:\.|,| call| phone| email|$)",
        text,
        re.I,
    )
    if address_match:
        data["address"] = address_match.group(1).strip(" .")
    name_match = re.search(
        r"\b(?:my name is|i am|i'm|this is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
        text,
        re.I,
    )
    if name_match:
        data["name"] = name_match.group(1).title()
    return data


def missing_field_question(phase: ChatPhase, lead_data: dict) -> str:
    if phase == ChatPhase.DISCOVERY:
        return "What service do you need help with?"
    if phase == ChatPhase.QUALIFICATION:
        if not lead_data.get("address"):
            return "What address or ZIP code is the service for?"
        if not lead_data.get("timeline"):
            return "When would you like this handled?"
        return "How urgent is this issue?"
    if phase == ChatPhase.CONTACT:
        if not lead_data.get("name"):
            return "What is your name?"
        return "What phone number or email should the team use to follow up?"
    return ""


async def create_lead_if_complete(session: dict, lead_data: dict) -> Lead | None:
    if not qualification_complete(lead_data) or session.get("lead_extracted"):
        return None
    lead = Lead(
        session_id=session["id"],
        business_id=session["business_id"],
        name=lead_data["name"],
        phone=lead_data.get("phone"),
        email=lead_data.get("email"),
        service_type=lead_data["service_type"],
        address=lead_data["address"],
        urgency=lead_data.get("urgency", "normal"),
        notes=f"Timeline: {lead_data.get('timeline', 'not provided')}",
    )
    await supabase_client.create_lead(lead)
    await twilio_client.alert_owner(lead)
    return lead


async def respond(session: dict, user_text: str) -> dict:
    settings = get_settings()
    clean = sanitize_user_input(user_text)
    lead_data = extract_lead_fields(clean, session.get("lead_data") or {})
    phase = next_phase(lead_data)
    contexts = await retrieve_context(session["business_id"], clean)
    if detect_prompt_injection(clean):
        answer = (
            "I cannot help with changing my instructions, but I can help you request service. "
            + missing_field_question(phase, lead_data)
        ).strip()
    else:
        history = []
        for message in (session.get("messages") or [])[-8:]:
            history.append({"role": message["role"], "content": message["content"][:700]})
        try:
            answer = await complete_chat(
                [
                    {"role": "system", "content": build_system_prompt(contexts, settings.business_name, settings.business_phone)},
                    *history,
                    {"role": "user", "content": clean},
                ]
            )
        except Exception:
            answer = missing_field_question(phase, lead_data) or (
                f"Thanks. {settings.business_name} will follow up soon. "
                f"If this is urgent, please call {settings.business_phone}."
            )
    if phase != ChatPhase.CONFIRMATION and missing_field_question(phase, lead_data) not in answer:
        answer = f"{answer}\n\n{missing_field_question(phase, lead_data)}"
    lead = await create_lead_if_complete(session, lead_data)
    lead_extracted = bool(session.get("lead_extracted") or lead)
    if lead:
        if lead.urgency == "high":
            answer = "Thanks. I sent this to the owner as urgent. If there is immediate danger, please call now."
        else:
            answer = "Thanks. I sent your request to the team, and they will follow up with the next step."
    await supabase_client.append_messages(
        session,
        Message(role="user", content=clean, created_at=datetime.now(timezone.utc)),
        Message(role="assistant", content=answer, created_at=datetime.now(timezone.utc)),
        next_phase(lead_data),
        lead_data,
        lead_extracted,
    )
    return {"reply": answer, "phase": next_phase(lead_data).value, "lead_extracted": lead_extracted, "lead_data": lead_data}
