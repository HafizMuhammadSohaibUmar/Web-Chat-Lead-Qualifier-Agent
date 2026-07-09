# LeadPilot AI Website Chat Widget Agent

Embeddable AI chat widget for home service contractor websites. It answers business-specific questions from a RAG knowledge base, qualifies service leads, creates Supabase leads, and alerts the owner by SMS.

## What It Does

- One-script vanilla JavaScript widget: `static/widget.js`
- FastAPI chat API with SSE streaming
- Per-business RAG knowledge base using local `all-MiniLM-L6-v2` embeddings
- Supabase pgvector storage
- Gemini 2.5 Flash primary model with Mistral fallback through LiteLLM
- Lead qualification flow: discovery, qualification, contact, confirmation
- JWT session tokens with 30-minute inactivity expiry
- Session and IP rate limits
- Prompt-injection refusal behavior
- PII blocking for credit-card and SSN patterns
- Owner SMS alert on qualified lead
- Analytics endpoint

## Related Agents

| Agent | Name |
| --- | --- |
| 1 | LeadPilot AI Voice Agent |
| 2 | LeadPilot AI Missed Call Text-Back Agent |
| 3 | LeadPilot AI Outbound Follow-Up Agent |
| 4 | LeadPilot AI Review Request Agent |
| 5 | LeadPilot AI Website Chat Widget Agent |

## Widget Embed

```html
<script
  src="https://ai-chat-widget-agent.sohaib.systems/static/widget.js"
  data-business-id="default-business"
  data-api-base="https://ai-chat-widget-agent.sohaib.systems"
  data-variant="friendly"
  data-fallback-phone="+15551234567">
</script>
```

`data-variant` supports A/B testing greetings. Current variants include default/friendly behavior and `urgent`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/widget/init` | Create JWT-backed chat session |
| `POST` | `/chat` | Non-streaming chat response |
| `GET` | `/chat/stream` | SSE streaming chat response |
| `POST` | `/admin/onboard/{business_id}` | Load and embed knowledge base |
| `GET` | `/analytics/{business_id}` | 7-day widget metrics |
| `GET` | `/demo` | Local browser demo |
| `GET` | `/health` | Health check |

Admin endpoints require:

```text
X-LeadPilot-Key: your_admin_key
```

## Supabase

Run:

```text
db/migrations/001_init.sql
```

This enables `vector` and creates:

- `knowledge_chunks`
- `chat_sessions`
- `chat_leads`

## Knowledge Onboarding

```bash
curl -X POST https://ai-chat-widget-agent.sohaib.systems/admin/onboard/default-business \
  -H "Content-Type: application/json" \
  -H "X-LeadPilot-Key: your_admin_key" \
  -d '{
    "business_name": "Sohaib Systems",
    "business_type": "home services",
    "service_area_cities": ["Lahore", "Islamabad"],
    "services_offered": ["AC repair", "plumbing", "electrical"],
    "faqs": [{"question": "Do you handle emergencies?", "answer": "Yes, urgent calls are prioritized."}],
    "business_hours": "Mon-Sat 9am-6pm",
    "emergency_availability": "Available for urgent requests",
    "special_notes": "Ask for service type, location, timeline, and contact details."
  }'
```

## Local Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8005
```

Open:

```text
http://localhost:8005/demo
```

## Production Notes

- `ALLOWED_ORIGINS` must list exact client domains. Wildcards are blocked.
- Keep `SMS_DRY_RUN=true` for public demos.
- Rotate `JWT_SECRET` and `ADMIN_API_KEY` before deployment.
- The widget has no framework or build step.
- The fallback message tells visitors to call the configured phone if the API is down.
