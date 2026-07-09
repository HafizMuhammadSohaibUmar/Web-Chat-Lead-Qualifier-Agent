"""Knowledge-base onboarding."""
from typing import Any

from integrations.supabase_client import supabase_client
from rag.embedder import get_embedder


def build_chunks(payload: dict[str, Any]) -> list[dict]:
    chunks: list[dict] = []
    business_name = payload["business_name"]
    chunks.append({
        "chunk_type": "business_profile",
        "content": (
            f"{business_name} is a {payload.get('business_type', 'home service business')}. "
            f"Service cities: {', '.join(payload.get('service_area_cities') or [])}. "
            f"Hours: {payload.get('business_hours', 'not provided')}. "
            f"Emergency availability: {payload.get('emergency_availability', 'not provided')}."
        ),
        "metadata": {"business_name": business_name},
    })
    for service in payload.get("services_offered") or []:
        chunks.append({"chunk_type": "service", "content": f"{business_name} offers {service}.", "metadata": {"service": service}})
    for faq in payload.get("faqs") or []:
        if isinstance(faq, dict):
            content = f"FAQ: {faq.get('question')} Answer: {faq.get('answer')}"
        else:
            content = f"FAQ: {faq}"
        chunks.append({"chunk_type": "faq", "content": content, "metadata": {}})
    if payload.get("special_notes"):
        chunks.append({"chunk_type": "special_notes", "content": payload["special_notes"], "metadata": {}})
    return chunks


async def onboard_knowledge_base(business_id: str, payload: dict[str, Any]) -> dict:
    embedder = get_embedder()
    chunks = build_chunks(payload)
    for chunk in chunks:
        await supabase_client.upsert_knowledge_chunk(
            business_id,
            chunk["content"],
            embedder.embed(chunk["content"]),
            chunk["chunk_type"],
            chunk["metadata"],
        )
    return {"business_id": business_id, "chunks_loaded": len(chunks)}
