"""Qualification flow tests."""
import pytest

from conversation.chain import extract_lead_fields, respond
from models.session import ChatSession


def test_extract_lead_fields_complete_message():
    data = extract_lead_fields("My name is Jane Doe. Need AC repair today at 123 Main Street. Call +15551234567")

    assert data["service_type"] == "hvac"
    assert data["urgency"] == "high"
    assert data["name"] == "Jane Doe"
    assert data["phone"] == "+15551234567"
    assert "123 Main" in data["address"]


@pytest.mark.asyncio
async def test_qualification_flow_creates_lead(monkeypatch):
    created = {}

    async def fake_context(_business_id, _query):
        return [{"content": "Sohaib Systems repairs AC units."}]

    async def fake_lead(lead):
        created["lead"] = lead
        return lead.model_dump(mode="json")

    async def fake_alert(_lead):
        return True

    async def fake_append(*_args, **_kwargs):
        return None

    monkeypatch.setattr("conversation.chain.retrieve_context", fake_context)
    monkeypatch.setattr("conversation.chain.supabase_client.create_lead", fake_lead)
    monkeypatch.setattr("conversation.chain.twilio_client.alert_owner", fake_alert)
    monkeypatch.setattr("conversation.chain.supabase_client.append_messages", fake_append)
    session = ChatSession(business_id="test-business", session_token="token").model_dump(mode="json")
    result = await respond(session, "My name is Jane Doe. Need AC repair today at 123 Main Street. Call +15551234567")

    assert result["lead_extracted"] is True
    assert created["lead"].service_type == "hvac"
