-- ============================================================
-- ONE2LVOS: public.lumenis_dreams for the LUMENIS Supabase project
-- (ref mleqofawbgtzolutbmyp). Additive only. Separate from
-- public.memories (factual memory): dreams never go there.
--
-- Holds Lumenis dream-cycle text word for word with an embedding
-- (nvidia/nemotron-3.5-embed-1b, 2048 dims). Every row is forced to
-- be labelled a dream: record_class='dream', is_dream=true,
-- verified_fact=false (CHECK constraints).
-- No ANN index: pgvector HNSW/IVFFlat cap at 2000 dims, and an exact
-- scan over a few hundred rows is fast.
-- Access: service_role only (RLS on, no policies).
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.lumenis_dreams (
    id               TEXT PRIMARY KEY,
    record_class     TEXT NOT NULL DEFAULT 'dream' CHECK (record_class = 'dream'),
    is_dream         BOOLEAN NOT NULL DEFAULT TRUE CHECK (is_dream),
    verified_fact    BOOLEAN NOT NULL DEFAULT FALSE CHECK (NOT verified_fact),
    label            TEXT NOT NULL,
    batch_id         TEXT NOT NULL,
    kind             TEXT NOT NULL,
    cycle_number     INT  NOT NULL,
    phase            TEXT NOT NULL,
    phase_index      INT  NOT NULL,
    session_id       TEXT NOT NULL,
    text             TEXT NOT NULL,
    text_sha256      TEXT NOT NULL,
    text_chars       INT  NOT NULL,
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding_model  TEXT NOT NULL,
    embedding        extensions.vector(2048) NOT NULL,
    imported_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lumenis_dreams_batch_cycle ON public.lumenis_dreams (batch_id, cycle_number, phase_index);

ALTER TABLE public.lumenis_dreams ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lumenis_dreams FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.lumenis_dreams TO service_role;

CREATE OR REPLACE FUNCTION public.match_lumenis_dreams(
    query_embedding extensions.vector(2048),
    match_count INT DEFAULT 5
)
RETURNS TABLE (id TEXT, label TEXT, batch_id TEXT, kind TEXT, cycle_number INT, phase TEXT,
               session_id TEXT, text TEXT, similarity FLOAT)
LANGUAGE sql STABLE
SET search_path = public, extensions
AS $$
    SELECT d.id, d.label, d.batch_id, d.kind, d.cycle_number, d.phase, d.session_id, d.text,
           1 - (d.embedding <=> query_embedding) AS similarity
    FROM public.lumenis_dreams d
    WHERE d.record_class = 'dream' AND d.is_dream
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
$$;

REVOKE ALL ON FUNCTION public.match_lumenis_dreams(extensions.vector, INT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.match_lumenis_dreams(extensions.vector, INT) TO service_role;

NOTIFY pgrst, 'reload schema';
