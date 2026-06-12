-- Sharper Phase 3 Step 5: persistence schema
-- Run once in the Supabase dashboard SQL editor (Database > SQL Editor > New query).

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

-- Stores one row per lint call.
create table critiques (
    id                 uuid primary key default gen_random_uuid(),
    user_id            text not null,   -- Clerk user_id (sub claim); 'anon' for unauthenticated
    question           text not null,
    overall_assessment text not null,
    created_at         timestamptz not null default now()
);

-- One row per Finding returned in the critique.
create table findings (
    id                uuid primary key default gen_random_uuid(),
    critique_id       uuid not null references critiques(id) on delete cascade,
    rubric_item       text not null,
    severity          text not null,
    quoted_span       text not null,
    issue             text not null,
    explanation       text not null,
    suggested_rewrite text
);

-- One row each time the user clicks "accept" on a suggested rewrite.
create table rewrite_actions (
    id          uuid primary key default gen_random_uuid(),
    finding_id  uuid not null references findings(id) on delete cascade,
    user_id     text not null,
    accepted_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

create index on critiques (user_id, created_at desc);
create index on findings (critique_id);
create index on rewrite_actions (finding_id);

-- ---------------------------------------------------------------------------
-- Row-level security
--
-- Design:
--   - The FastAPI backend connects with SUPABASE_SERVICE_ROLE_KEY, which
--     bypasses RLS entirely. All DB writes go through the backend only.
--   - The anon key is never sent to the frontend and is not used in any
--     backend code. With RLS enabled and no permissive policies, the anon
--     key has ZERO access to these tables (Supabase deny-all default).
--   - We add explicit DENY policies so the intent is clear and a future
--     accidental anon-key usage fails loudly rather than silently.
-- ---------------------------------------------------------------------------

alter table critiques      enable row level security;
alter table findings       enable row level security;
alter table rewrite_actions enable row level security;

-- Explicit deny-all for the anon role (belt-and-suspenders over the default).
create policy "anon: no select" on critiques       for select to anon using (false);
create policy "anon: no insert" on critiques       for insert to anon with check (false);
create policy "anon: no select" on findings        for select to anon using (false);
create policy "anon: no insert" on findings        for insert to anon with check (false);
create policy "anon: no select" on rewrite_actions for select to anon using (false);
create policy "anon: no insert" on rewrite_actions for insert to anon with check (false);

-- authenticated role also blocked: all access goes through the service-role
-- backend, never directly from a browser Supabase client.
create policy "authenticated: no select" on critiques       for select to authenticated using (false);
create policy "authenticated: no insert" on critiques       for insert to authenticated with check (false);
create policy "authenticated: no select" on findings        for select to authenticated using (false);
create policy "authenticated: no insert" on findings        for insert to authenticated with check (false);
create policy "authenticated: no select" on rewrite_actions for select to authenticated using (false);
create policy "authenticated: no insert" on rewrite_actions for insert to authenticated with check (false);
