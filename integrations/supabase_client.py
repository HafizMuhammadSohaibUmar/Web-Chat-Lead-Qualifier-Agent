"""Async Supabase PostgREST and RPC client."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from config import get_settings
from models.lead import Lead
from models.session import ChatPhase, ChatSession, Message


def _mask_contact(value: str | None) -> str:
    if not value:
        return ""
    if "@" in value:
        name, _, domain = value.partition("@")
        return f"{name[:2]}***@{domain}" if domain else "***"
    return f"{value[:3]}***{value[-4:]}" if len(value) >= 7 else "***"


class SupabaseClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/rest/v1/{path}"

    async def _request(self, method: str, table: str, *,
                       params: Optional[dict] = None, json: Any = None) -> list[dict]:
        if not self.base_url or not get_settings().supabase_key:
            return []
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(method, self._url(table), headers=self.headers, params=params, json=json)
            response.raise_for_status()
        return response.json() if response.content else []

    async def upsert_knowledge_chunk(self, business_id: str, content: str,
                                     embedding: list[float], chunk_type: str,
                                     metadata: dict) -> dict:
        rows = await self._request(
            "POST",
            "knowledge_chunks",
            json={
                "business_id": business_id,
                "content": content,
                "embedding": embedding,
                "chunk_type": chunk_type,
                "metadata": metadata,
            },
        )
        return rows[0] if rows else {}

    async def list_knowledge_chunks(self, business_id: str) -> list[dict]:
        return await self._request(
            "GET",
            "knowledge_chunks",
            params={"business_id": f"eq.{business_id}", "select": "*", "limit": "1000"},
        )

    async def create_session(self, session: ChatSession) -> dict:
        rows = await self._request("POST", "chat_sessions", json=session.model_dump(mode="json"))
        return rows[0] if rows else session.model_dump(mode="json")

    async def get_session(self, token: str, business_id: str) -> dict | None:
        rows = await self._request(
            "GET",
            "chat_sessions",
            params={
                "session_token": f"eq.{token}",
                "business_id": f"eq.{business_id}",
                "select": "*",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    async def update_session(self, session_id: str, **fields: Any) -> None:
        await self._request("PATCH", "chat_sessions", params={"id": f"eq.{session_id}"}, json=fields)

    async def append_messages(self, session: dict, user: Message, assistant: Message,
                              phase: ChatPhase, lead_data: dict, lead_extracted: bool) -> None:
        messages = list(session.get("messages") or [])
        messages.extend([user.model_dump(mode="json"), assistant.model_dump(mode="json")])
        await self.update_session(
            session["id"],
            messages=messages,
            phase=phase.value,
            lead_data=lead_data,
            lead_extracted=lead_extracted,
            message_count=(session.get("message_count") or 0) + 1,
            last_active_at=datetime.now(timezone.utc).isoformat(),
        )

    async def create_lead(self, lead: Lead) -> dict:
        rows = await self._request("POST", "chat_leads", json=lead.model_dump(mode="json"))
        return rows[0] if rows else lead.model_dump(mode="json")

    async def sessions_created_today(self, business_id: str) -> int:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        rows = await self._request(
            "GET",
            "chat_sessions",
            params={"business_id": f"eq.{business_id}", "created_at": f"gte.{since.isoformat()}", "select": "id"},
        )
        return len(rows)

    async def analytics(self, business_id: str) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        sessions = await self._request(
            "GET",
            "chat_sessions",
            params={"business_id": f"eq.{business_id}", "created_at": f"gte.{since.isoformat()}", "select": "*"},
        )
        leads = await self._request(
            "GET",
            "chat_leads",
            params={"business_id": f"eq.{business_id}", "created_at": f"gte.{since.isoformat()}", "select": "*"},
        )
        services: dict[str, int] = {}
        for lead in leads:
            service = lead.get("service_type") or "unknown"
            services[service] = services.get(service, 0) + 1
        qualified = [s for s in sessions if s.get("lead_extracted")]
        avg = round(sum(s.get("message_count") or 0 for s in qualified) / (len(qualified) or 1), 2)
        return {
            "message_count_7d": sum(s.get("message_count") or 0 for s in sessions),
            "leads_captured_7d": len(leads),
            "avg_messages_to_qualification": avg,
            "top_service_requests": sorted(services.items(), key=lambda item: item[1], reverse=True)[:5],
        }

    async def demo_snapshot(self, business_id: str) -> dict:
        sessions = await self._request(
            "GET",
            "chat_sessions",
            params={
                "business_id": f"eq.{business_id}",
                "select": "phase,lead_extracted,message_count,created_at,last_active_at",
                "order": "last_active_at.desc",
                "limit": "6",
            },
        )
        leads = await self._request(
            "GET",
            "chat_leads",
            params={
                "business_id": f"eq.{business_id}",
                "select": "phone,email,service_type,urgency,created_at",
                "order": "created_at.desc",
                "limit": "6",
            },
        )
        chunks = await self._request(
            "GET",
            "knowledge_chunks",
            params={
                "business_id": f"eq.{business_id}",
                "select": "chunk_type,created_at",
                "order": "created_at.desc",
                "limit": "6",
            },
        )
        return {
            "tables": {
                "chat_sessions": {
                    "sample": [
                        {
                            "phase": row.get("phase"),
                            "lead_extracted": bool(row.get("lead_extracted")),
                            "message_count": row.get("message_count"),
                            "last_active_at": row.get("last_active_at"),
                        }
                        for row in sessions
                    ],
                },
                "chat_leads": {
                    "sample": [
                        {
                            "phone": _mask_contact(row.get("phone")),
                            "email": _mask_contact(row.get("email")),
                            "service_type": row.get("service_type"),
                            "urgency": row.get("urgency"),
                            "created_at": row.get("created_at"),
                        }
                        for row in leads
                    ],
                },
                "knowledge_chunks": {
                    "sample": [
                        {
                            "chunk_type": row.get("chunk_type"),
                            "created_at": row.get("created_at"),
                        }
                        for row in chunks
                    ],
                },
            }
        }

    async def health_check(self) -> dict:
        try:
            await self._request("GET", "chat_sessions", params={"select": "id", "limit": "1"})
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


supabase_client = SupabaseClient()
