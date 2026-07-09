# Decisions

## 1. Vanilla Widget

The widget is one JavaScript file with no framework and no build step. That makes it easy to embed on contractor websites and keeps client installation simple.

## 2. Local Embeddings

The knowledge base uses `sentence-transformers/all-MiniLM-L6-v2` locally. This avoids paid embedding APIs and produces 384-dimensional vectors that fit the required pgvector schema.

## 3. Deterministic Embedding Fallback

Tests and lightweight environments can run without downloading the transformer model. The embedder falls back to deterministic hashed 384-dimensional vectors. Production still installs and uses sentence-transformers.

## 4. CORS By Exact Origin

Wildcard CORS is blocked at startup. A public widget API must only allow the client domains that are supposed to embed it.

## 5. Prompt-Injection Defense

The conversation layer sanitizes user input, detects common prompt-injection attempts, and refuses requests to reveal or override instructions. Tests cover this explicitly.

## 6. Sensitive PII Blocking

Credit-card and SSN-like patterns are blocked before Supabase inserts. The widget collects normal contact details only: name, phone, email, address or ZIP, service type, timeline, and urgency.
