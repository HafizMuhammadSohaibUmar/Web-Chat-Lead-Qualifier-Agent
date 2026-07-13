# LeadPilot AI Web Chat Lead Qualifier Agent

Embeddable AI chat widget for home-service contractor websites. The agent answers business-specific questions from a per-business knowledge base, qualifies service requests, stores conversation state, creates structured leads, and can notify the owner by SMS.

## Live Demo

- Live demo: `https://web-chat-lead-qualifier-agent.sohaib.systems/demo`
- Repository: `https://github.com/HafizMuhammadSohaibUmar/Web-Chat-Lead-Qualifier-Agent`

How to evaluate the demo:

1. Open the live demo and click the chat bubble in the bottom-right corner.
2. Ask a business-knowledge question, for example: `Do you handle emergency AC repair?`
3. Start a lead request, for example: `I need plumbing help at 123 Main Street today.`
4. Add contact details, for example: `My name is Jane Doe and my phone is 555-222-1000.`
5. Watch the safe database preview update with masked session/lead activity. It intentionally hides message bodies, names, addresses, session tokens, and raw knowledge content.

## What It Does

- Provides a one-script vanilla JavaScript widget in `static/widget.js`.
- Creates a JWT-backed chat session on widget initialization.
- Streams assistant responses through Server-Sent Events.
- Retrieves top knowledge chunks from Supabase pgvector.
- Uses local `all-MiniLM-L6-v2` embeddings for knowledge onboarding.
- Uses Gemini 2.5 Flash through LiteLLM, with Mistral fallback.
- Tracks the conversation phase: discovery, qualification, contact, confirmation.
- Extracts service type, address or ZIP, urgency, timeline, name, phone, and email.
- Creates a Supabase `chat_leads` row when qualification is complete.
- Sends owner SMS alerts through Twilio when configured.
- Blocks obvious credit-card and SSN patterns before inserting user content.
- Includes prompt-injection defense tests.

## Architecture

```text
Contractor Website
  -> <script src="/static/widget.js">
  -> POST /widget/init
  -> JWT session token
  -> GET /chat/stream
  -> input sanitization + prompt-injection checks
  -> Supabase pgvector retrieval
  -> LiteLLM Gemini primary / Mistral fallback
  -> phase tracking + lead extraction
  -> Supabase chat_sessions + chat_leads
  -> optional Twilio owner alert
```

## Engineering Signals

- The widget has no frontend framework and no build step.
- CORS is configured from explicit origins rather than wildcard access.
- Rate limits are enforced per session and per IP.
- Knowledge retrieval is per business, not a global shared prompt.
- Sensitive demo data is masked before being displayed on the public page.
- The chat endpoint can fall back gracefully when the model or API is unavailable.

## Related AI Systems

| System | Purpose | Live Demo | Repository |
| --- | --- | --- | --- |
| LeadPilot AI Voice Agent | Inbound phone agent for call qualification, emergency detection, and lead logging. | [Live Demo](https://leadpilotai.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/LeadPilotAI) |
| Missed Call Text-Back AI Agent | SMS recovery and qualification after no-answer or busy calls. | [Live Demo](https://missed-call-text-back-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Missed-Call-Text-Back-AI-Agent) |
| Outbound Follow-Up AI Agent | Estimate, no-show, re-engagement, and seasonal follow-up campaigns. | [Live Demo](https://outbound-followup-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Outbound-Follow-Up-AI-Agent) |
| AI Auto Review Request Agent | Sentiment-aware post-job review and private feedback routing. | [Live Demo](https://ai-review-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/AI-Auto-Review-Request-Agent) |
| Web Chat Lead Qualifier Agent | Embeddable RAG chat widget for contractor websites. | [Live Demo](https://web-chat-lead-qualifier-agent.sohaib.systems/demo) | **This repo** |
| Personal AI Agent | Self-hosted task, planning, and local-calendar assistant with LangGraph tools. | [Live Demo](https://personal-ai-agent.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Personal-AI-Agent) |
| Invoxia AI for ERPNext | Frappe/ERPNext assistant layer for navigation, voice input foundations, and live ERP answers. | [Live Demo](https://invoxia.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/InvoxiaAI-ERPNext) |

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

`data-variant` supports alternate greetings for A/B testing. The fallback phone is shown if the API cannot initialize or stream a response.

## API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/widget/init` | Create a JWT-backed widget session |
| `POST` | `/chat` | Non-streaming chat response |
| `GET` | `/chat/stream` | SSE streaming chat response |
| `POST` | `/admin/onboard/{business_id}` | Embed a business knowledge profile |
| `GET` | `/analytics/{business_id}` | 7-day message and lead metrics |
| `GET` | `/demo` | Browser demo page |
| `GET` | `/demo/snapshot` | Sanitized public demo preview |
| `GET` | `/health` | Health check |

Admin endpoints require `X-LeadPilot-Key`.

## Supabase Schema

Run `db/migrations/001_init.sql` before starting the service. It enables `vector` and creates:

- `knowledge_chunks`
- `chat_sessions`
- `chat_leads`

## Knowledge Onboarding

```bash
curl -X POST http://localhost:8005/admin/onboard/default-business \
  -H "Content-Type: application/json" \
  -H "X-LeadPilot-Key: your_admin_key" \
  -d '{
    "business_name": "Acme Home Services",
    "business_type": "home services",
    "service_area_cities": ["Lahore", "Islamabad"],
    "services_offered": ["AC repair", "plumbing", "electrical"],
    "faqs": [{"question": "Do you handle emergencies?", "answer": "Yes, urgent calls are prioritized."}],
    "business_hours": "Mon-Sat 9am-6pm",
    "emergency_availability": "Available for urgent requests",
    "special_notes": "Ask for service type, location, timeline, and contact details."
  }'
```

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8005
```

Open `http://localhost:8005/demo`.

## Configuration Notes

- Set `ALLOWED_ORIGINS` to the exact domains allowed to embed the widget.
- Set `JWT_SECRET` and `ADMIN_API_KEY` to long random values before exposing admin endpoints.
- Keep `SMS_DRY_RUN=true` when evaluating the public demo without sending owner alerts.
- Configure `GEMINI_API_KEY`, `MISTRAL_API_KEY`, Supabase credentials, and Twilio credentials according to the features being tested.
