create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists knowledge_chunks (
    id          uuid primary key default gen_random_uuid(),
    business_id text not null,
    content     text not null,
    embedding   vector(384) not null,
    chunk_type  text not null,
    metadata    jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

create index if not exists idx_knowledge_chunks_business
    on knowledge_chunks (business_id, chunk_type);

create index if not exists idx_knowledge_chunks_embedding
    on knowledge_chunks using ivfflat (embedding vector_cosine_ops);

create table if not exists chat_sessions (
    id             uuid primary key default gen_random_uuid(),
    business_id    text not null,
    session_token  text not null,
    messages       jsonb not null default '[]'::jsonb,
    phase          text not null default 'discovery',
    lead_extracted boolean not null default false,
    lead_data      jsonb not null default '{}'::jsonb,
    message_count  integer not null default 0,
    created_at     timestamptz not null default now(),
    last_active_at timestamptz not null default now()
);

create index if not exists idx_chat_sessions_business_created
    on chat_sessions (business_id, created_at desc);

create unique index if not exists idx_chat_sessions_token
    on chat_sessions (session_token);

create table if not exists chat_leads (
    id           uuid primary key default gen_random_uuid(),
    session_id   uuid not null,
    business_id  text not null,
    name         text not null,
    phone        text,
    email        text,
    service_type text not null,
    address      text not null,
    urgency      text not null,
    notes        text not null default '',
    created_at   timestamptz not null default now()
);

create index if not exists idx_chat_leads_business_created
    on chat_leads (business_id, created_at desc);
