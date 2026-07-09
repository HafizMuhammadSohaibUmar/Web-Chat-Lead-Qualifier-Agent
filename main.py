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
        <!doctype html><html><head><title>Chat Widget Demo</title></head>
        <body><h1>Website Chat Widget Demo</h1>
        <script src="/static/widget.js" data-business-id="default-business" data-api-base="" data-variant="friendly"></script>
        </body></html>
        """
    )


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
