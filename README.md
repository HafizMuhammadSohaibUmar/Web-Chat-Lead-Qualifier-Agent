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

## Architecture

```text
Client Website
  -> one-script widget.js embed
  -> /widget/init JWT session
  -> /chat/stream SSE response
  -> prompt-injection and PII checks
  -> RAG retrieval from Supabase pgvector
  -> LiteLLM Gemini primary / Mistral fallback
  -> lead extraction and phase tracking
  -> Supabase chat_leads + owner SMS alert
```

## What It Proves

- A contractor website can add AI lead qualification through one script tag.
- Business-specific answers can come from a per-client RAG knowledge base instead of generic chatbot text.
- Chat systems need CORS boundaries, session limits, IP limits, PII blocking, and prompt-injection tests.
- The widget remains framework-free and deployable without a frontend build step.

## Related AI Systems

| System | Purpose | Links |
| --- | --- | --- |
| LeadPilot AI Voice Agent | Inbound phone agent for call qualification, emergency detection, and lead logging. | [Live](https://leadpilotai.sohaib.systems/) · [Repo](https://github.com/HafizMuhammadSohaibUmar/LeadPilotAI) |
| Missed Call Text-Back AI Agent | SMS recovery and qualification after no-answer or busy calls. | [Live](https://missed-call-text-back-ai-agent.sohaib.systems/demo) · [Repo](https://github.com/HafizMuhammadSohaibUmar/Missed-Call-Text-Back-AI-Agent) |
| Outbound Follow-Up AI Agent | Estimate, no-show, re-engagement, and seasonal follow-up campaigns. | [Live](https://outbound-followup-ai-agent.sohaib.systems/demo) · [Repo](https://github.com/HafizMuhammadSohaibUmar/Outbound-Follow-Up-AI-Agent) |
| AI Auto Review Request Agent | Sentiment-aware post-job review and private feedback routing. | [Live](https://ai-review-agent.sohaib.systems/demo) · [Repo](https://github.com/HafizMuhammadSohaibUmar/AI-Auto-Review-Request-Agent) |
| Web Chat Lead Qualifier Agent | Embeddable RAG chat widget for contractor websites. | [Live](https://web-chat-lead-qualifier-agent.sohaib.systems/demo) · [Repo](https://github.com/HafizMuhammadSohaibUmar/Web-Chat-Lead-Qualifier-Agent) |
| Personal AI Agent | Local task, planning, and calendar assistant with LangGraph tools. | [Live](https://personal-ai-agent.sohaib.systems/) · [Repo](https://github.com/HafizMuhammadSohaibUmar/Personal-AI-Agent) |
| Invoxia AI for ERPNext | Frappe/ERPNext assistant layer for navigation, voice input foundations, and live ERP answers. | [Live](https://invoxia.sohaib.systems/) · [Repo](https://github.com/HafizMuhammadSohaibUmar/InvoxiaAI-ERPNext) |

## Widget Embed

```html
<script
  src="https://web-chat-lead-qualifier-agent.sohaib.systems/static/widget.js"
  data-business-id="default-business"
  data-api-base="https://web-chat-lead-qualifier-agent.sohaib.systems"
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
