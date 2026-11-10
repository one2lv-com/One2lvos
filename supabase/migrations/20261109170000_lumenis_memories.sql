-- ============================================================
-- ONE2LVOS: public.memories for the LUMENIS Supabase project
-- (ref mleqofawbgtzolutbmyp). Additive only.
--
-- Columns mirror the reactor's own memory record, the FluxCompass
-- `facts` table in lumenis_reactor_core/compass.py
-- (id, session_id, key, value, source, created_at). ids stay TEXT
-- because some existing compass ids and session ids are not UUIDs.
-- created_at is TIMESTAMPTZ like the other reactor tables.
--
-- Access: service_role only. RLS on, no policies, anon and
-- authenticated revoked, so the publishable key cannot read it.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.memories (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id  TEXT,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    source      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- compass.py: idx_facts_key, recall/get_all ORDER BY created_at DESC,
-- per-session reads filtered on session_id
CREATE INDEX IF NOT EXISTS idx_memories_key ON public.memories (key);
CREATE INDEX IF NOT EXISTS idx_memories_created ON public.memories (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_session_created ON public.memories (session_id, created_at DESC);

ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.memories FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.memories TO service_role;

NOTIFY pgrst, 'reload schema';
