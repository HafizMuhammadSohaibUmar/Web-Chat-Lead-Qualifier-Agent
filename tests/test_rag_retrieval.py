"""RAG retrieval tests."""
import pytest

from rag.embedder import get_embedder
from rag.retriever import retrieve_context


@pytest.mark.asyncio
async def test_rag_retrieval_returns_top_matching_chunks(monkeypatch):
    embedder = get_embedder()
    chunks = [
        {"content": "We repair AC systems and furnaces.", "embedding": embedder.embed("AC repair furnace"), "chunk_type": "service"},
        {"content": "We clean gutters.", "embedding": embedder.embed("gutter cleaning"), "chunk_type": "service"},
    ]

    async def fake_chunks(_business_id):
        return chunks

    monkeypatch.setattr("rag.retriever.supabase_client.list_knowledge_chunks", fake_chunks)
    result = await retrieve_context("test-business", "my AC is broken")

    assert result[0]["content"].startswith("We repair AC")
