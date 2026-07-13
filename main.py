"""LeadPilot AI Website Chat Widget Agent."""
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from admin.onboarding import KnowledgePayload, onboard_business
from config import get_settings
from conversation.chain import respond
from integrations.supabase_client import supabase_client
from logging_utils import log_event, setup_logging
from models.session import ChatRequest, ChatSession
from security import (
    assert_no_blocked_pii,
    create_session_token,
    enforce_ip_rate_limit,
    require_admin_key,
    verify_session_token,
)

logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log_event(logger, "AI chat widget agent starting", action="startup")
    yield
    log_event(logger, "AI chat widget agent stopping", action="shutdown")


settings = get_settings()
app = FastAPI(title="LeadPilot AI Website Chat Widget Agent", lifespan=lifespan)
if "*" in settings.origin_list:
    raise RuntimeError("CORS wildcard is not allowed for this widget service.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-LeadPilot-Key"],
)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def root():
    return {"service": "LeadPilot AI Website Chat Widget Agent", "health": "/health", "widget": "/static/widget.js"}


@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    if not get_settings().demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo disabled")
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Web Chat Lead Qualifier Agent Demo</title>
          <style>
            :root { color-scheme: dark; --gold:#C49A1A; --teal:#4FB39F; --cream:#F5F0E4; --muted:#9A9080; --card:#18160E; --line:rgba(255,255,255,0.08); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }
            * { box-sizing: border-box; }
            body { margin:0; min-height:100vh; background:radial-gradient(circle at top left, rgba(47,143,126,0.16), transparent 34%), #0A0908; color:var(--cream); }
            header { padding:42px clamp(20px,6vw,82px); border-bottom:1px solid var(--line); background:rgba(17,16,9,0.92); }
            .badge { display:inline-flex; border:1px solid rgba(79,179,159,0.28); background:rgba(79,179,159,0.12); color:var(--teal); border-radius:999px; padding:7px 12px; font-weight:800; font-size:13px; }
            h1 { margin:14px 0 10px; font-size:clamp(34px,5vw,62px); line-height:1; }
            p { color:var(--muted); line-height:1.7; max-width:760px; font-size:18px; }
            main { display:grid; grid-template-columns:1.05fr .95fr; gap:22px; padding:30px clamp(20px,6vw,82px) 80px; }
            section { background:linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)), var(--card); border:1px solid var(--line); border-radius:18px; padding:24px; }
            h2 { margin:0 0 14px; }
            .step { border-top:1px solid var(--line); padding:14px 0; color:var(--muted); }
            .step strong { color:var(--cream); display:block; margin-bottom:4px; }
            code { color:var(--teal); }
            .callout { margin-top:16px; border:1px solid rgba(196,154,26,0.22); border-left:3px solid var(--gold); border-radius:10px; padding:14px; background:rgba(196,154,26,0.08); color:var(--muted); }
            .metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:18px; }
            .metric { border:1px solid var(--line); border-radius:12px; padding:14px; background:#111009; }
            .metric strong { display:block; color:var(--cream); font-size:14px; margin-bottom:5px; }
            .metric span { color:var(--muted); font-size:13px; line-height:1.5; }
            .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:12px; margin-top:12px; background:#111009; }
            table { width:100%; border-collapse:collapse; min-width:520px; }
            th, td { text-align:left; border-bottom:1px solid var(--line); padding:10px 12px; font-size:14px; vertical-align:top; }
            th { color:var(--cream); background:rgba(255,255,255,0.04); }
            td { color:var(--muted); }
            .empty { color:var(--muted); border:1px dashed var(--line); border-radius:12px; padding:14px; margin-top:10px; }
            @media(max-width:900px){ main{grid-template-columns:1fr;} }
            @media(max-width:680px){ .metrics{grid-template-columns:1fr;} }
          </style>
        </head>
        <body>
          <header>
            <span class="badge">Demo mode</span>
            <h1>Web Chat Lead Qualifier Agent</h1>
            <p>An embeddable website chat agent for home-service contractors. It answers service questions from a business knowledge base, collects the details needed for a quote or dispatch, stores the conversation state, and creates a lead when the request is complete.</p>
            <div class="metrics">
              <div class="metric"><strong>Problem solved</strong><span>Website visitors often leave before calling. The widget turns service questions into structured lead intake.</span></div>
              <div class="metric"><strong>How to evaluate</strong><span>Open the chat bubble, ask a knowledge question, then provide service, address, urgency, name, and contact details.</span></div>
              <div class="metric"><strong>What to watch</strong><span>The agent should stream a reply, ask only for missing fields, and update the safe table preview without exposing private text.</span></div>
            </div>
          </header>
          <main>
            <section>
              <h2>Test Scenarios</h2>
              <div class="step"><strong>Ask a knowledge question</strong>Try: <code>Do you handle emergency AC repair?</code></div>
              <div class="step"><strong>Start a lead</strong>Try: <code>I need plumbing help at 123 Main Street today.</code></div>
              <div class="step"><strong>Complete contact details</strong>Try: <code>My name is Jane Doe and my phone is 555-222-1000.</code></div>
              <div class="callout">This page uses the same one-script widget that a contractor site would embed. Owner SMS alerts may be kept in dry-run mode for safe public testing.</div>
            </section>
            <section>
              <h2>What Happens Internally</h2>
              <div class="step"><strong>1. Session</strong><code>/widget/init</code> returns a JWT-backed session token.</div>
              <div class="step"><strong>2. Streaming</strong><code>/chat/stream</code> sends the answer through Server-Sent Events.</div>
              <div class="step"><strong>3. RAG</strong>The agent retrieves top knowledge chunks from Supabase pgvector.</div>
              <div class="step"><strong>4. Lead Capture</strong>When service, urgency, location, and contact fields are complete, a lead row is created.</div>
              <h2>Safe Database Preview</h2>
              <div class="callout">Masked Supabase snapshot. Session tokens, message bodies, names, addresses, and raw knowledge content are not exposed.</div>
              <div id="snapshot" class="snapshot">Loading sanitized table preview...</div>
            </section>
          </main>
          <script>
            async function refreshSnapshot() {
              try {
                const response = await fetch("/demo/snapshot");
                renderSnapshot(await response.json());
              } catch (error) {
                document.getElementById("snapshot").textContent = "Snapshot unavailable.";
              }
            }
            function renderSnapshot(data) {
              const root = document.getElementById("snapshot");
              const tables = data.tables || {};
              root.innerHTML = Object.entries(tables).map(([name, table]) => {
                const rows = table.sample || [];
                if (!rows.length) return `<h3>${title(name)}</h3><div class="empty">No recent demo-safe rows yet.</div>`;
                const cols = Object.keys(rows[0]);
                return `<h3>${title(name)}</h3><div class="table-wrap"><table><thead><tr>${cols.map(c => `<th>${title(c)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${cols.map(c => `<td>${escapeHtml(String(row[c] ?? ""))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
              }).join("");
            }
            function title(value) { return value.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()); }
            function escapeHtml(value) {
              return value.replace(/[&<>"']/g, (ch) => {
                if (ch === "&") return "&amp;";
                if (ch === "<") return "&lt;";
                if (ch === ">") return "&gt;";
                if (ch === '"') return "&quot;";
                return "&#39;";
              });
            }
            refreshSnapshot();
            setInterval(refreshSnapshot, 15000);
          </script>
          <script src="/static/widget.js" data-business-id="default-business" data-api-base="" data-variant="friendly" data-fallback-phone="+15551234567"></script>
        </body>
        </html>
        """
    )


@app.get("/demo/snapshot")
async def demo_snapshot():
    if not get_settings().demo_mode_enabled:
        return {"enabled": False}
    return await supabase_client.demo_snapshot(get_settings().business_id)


@app.post("/widget/init")
async def init_widget(request: Request):
    enforce_ip_rate_limit(request)
    payload = await request.json()
    business_id = payload.get("business_id") or get_settings().business_id
    if await supabase_client.sessions_created_today(business_id) >= get_settings().max_sessions_per_business_day:
        raise HTTPException(status_code=429, detail="Daily session limit reached.")
    token = create_session_token(business_id)
    session = ChatSession(business_id=business_id, session_token=token)
    await supabase_client.create_session(session)
    greeting = "Hi, how can we help with your home service project today?"
    if payload.get("variant") == "urgent":
        greeting = "Hi, tell us what is going on and how urgent it is. We will help route it."
    return {"token": token, "business_id": business_id, "greeting": greeting, "expires_in_minutes": get_settings().session_expiry_minutes}


async def _load_session(chat: ChatRequest) -> dict:
    claims = verify_session_token(chat.token)
    business_id = chat.business_id or claims["business_id"]
    session = await supabase_client.get_session(chat.token, business_id)
    if not session:
        fallback = ChatSession(business_id=business_id, session_token=chat.token)
        session = await supabase_client.create_session(fallback)
    last_active = session.get("last_active_at")
    if last_active:
        last = datetime.fromisoformat(str(last_active).replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - last > timedelta(minutes=get_settings().session_expiry_minutes):
            raise HTTPException(status_code=401, detail="Session expired")
    if (session.get("message_count") or 0) >= get_settings().max_messages_per_session:
        raise HTTPException(status_code=429, detail="Session message limit reached.")
    return session


@app.post("/chat")
async def chat(request: Request, chat_request: ChatRequest):
    enforce_ip_rate_limit(request)
    assert_no_blocked_pii(chat_request.message)
    session = await _load_session(chat_request)
    return await respond(session, chat_request.message)


@app.get("/chat/stream")
async def chat_stream(request: Request, token: str, message: str, business_id: str | None = None):
    enforce_ip_rate_limit(request)
    assert_no_blocked_pii(message)
    session = await _load_session(ChatRequest(token=token, message=message, business_id=business_id))
    result = await respond(session, message)

    async def events():
        for word in result["reply"].split(" "):
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
        yield f"data: {json.dumps({'done': True, 'phase': result['phase'], 'lead_extracted': result['lead_extracted']})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/admin/onboard/{business_id}", dependencies=[Depends(require_admin_key)])
async def onboard(business_id: str, payload: KnowledgePayload):
    return await onboard_business(business_id, payload)


@app.get("/analytics/{business_id}", dependencies=[Depends(require_admin_key)])
async def analytics(business_id: str):
    return await supabase_client.analytics(business_id)


@app.get("/health")
async def health():
    db = await supabase_client.health_check()
    return {
        "status": "healthy" if db.get("ok") else "degraded",
        "business_id": get_settings().business_id,
        "database": db,
        "cors_origins": get_settings().origin_list,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=get_settings().host, port=get_settings().port)
