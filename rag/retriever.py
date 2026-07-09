"""RAG retrieval helpers."""
import math

from integrations.supabase_client import supabase_client
from rag.embedder import get_embedder


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    total = sum(a * b for a, b in zip(left, right))
    l_norm = math.sqrt(sum(a * a for a in left)) or 1.0
    r_norm = math.sqrt(sum(b * b for b in right)) or 1.0
    return total / (l_norm * r_norm)


async def retrieve_context(business_id: str, query: str, *, top_k: int = 3) -> list[dict]:
    query_embedding = get_embedder().embed(query)
    chunks = await supabase_client.list_knowledge_chunks(business_id)
    ranked = []
    for chunk in chunks:
        embedding = chunk.get("embedding") or []
        if isinstance(embedding, str):
            embedding = [float(part) for part in embedding.strip("[]").split(",") if part.strip()]
        ranked.append({**chunk, "score": cosine_similarity(query_embedding, embedding)})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]
