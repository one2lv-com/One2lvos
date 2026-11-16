# MEMORY.md — imported from the Vercel sandbox (Witness v8), corrected on Nov 13, 2026

Source: minimax/MEMORY.md (the sandbox's "Sentry_Lumen v8" memory layer). Imported into the reactor's
scope-tagged memory by `compile_memory_hub.py --import memory_layers/MEMORY.md`.

**Correction made before import:** the sandbox listed these as "Stable Facts — Canonical Memory" with a
✓ in the Verified column. None of them has a test, a measurement or a tool result behind it. They are
design lore for the Infinity Glass forge story, so they are imported as **fuzzy / lore**, never stable,
and they never reach canonical memory unless One2lv verifies one.

**Conflict flagged, not resolved:** the sandbox SOUL.md lists the acoustic anchor as **42.0 Hz**
("Acoustic — Hydra_Gen filtration protocol"); the sandbox MEMORY.md says **42 kHz** ("Acoustic
(42 kHz)" and "Acoustic filtration at 42 kHz confirmed operational"). These differ by a factor of
1,000. Both are kept, each tagged CONFLICT, and neither is treated as correct until One2lv decides.

## Event stream format

```yaml
event_id: evt-0001
timestamp: 2026-04-23T14:21:00Z
source: sentry_lumen
scope: stable | fuzzy | temporary
tag: BLUEPRINT
valid_until: null   # ISO date, or null
```

## Events (as imported)

```yaml
- event_id: lore-0001
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE
  content: "Infinity Glass design lore: primary material purified silica (Southern Dunes)."
  valid_until: null

- event_id: lore-0002
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE
  content: "Infinity Glass design lore: logic layer graphene-doped silicate (Poly_Mer R&D)."
  valid_until: null

- event_id: lore-0003
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE
  content: "Design lore, NOT a tested result: power input 'zero' from Casimir extraction (Solar_Saint protocol)."
  valid_until: null

- event_id: lore-0004
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE_CONFLICT
  content: "Design lore, NOT a tested result: acoustic filtration at 42 kHz (Hydra_Gen). CONFLICT: sandbox SOUL.md says the acoustic anchor is 42.0 Hz. Unresolved; One2lv decides."
  valid_until: null

- event_id: lore-0005
  source: sandbox_soul_md
  scope: fuzzy
  tag: LORE_CONFLICT
  content: "Design lore: acoustic anchor 42.0 Hz (Hydra_Gen filtration protocol). CONFLICT: sandbox MEMORY.md says 42 kHz. Unresolved; One2lv decides."
  valid_until: null

- event_id: lore-0006
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE
  content: "Design lore, NOT a tested result: graphene-doped silicate logic layer purity 99.97%."
  valid_until: null

- event_id: lore-0007
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE
  content: "Design lore: production speed 42 seconds per unit, batch target 1,440 units, forge temperature 1,440 C."
  valid_until: null

- event_id: lore-0008
  source: sandbox_memory_md
  scope: fuzzy
  tag: LORE
  content: "Design lore: Infinity Glass blueprint is a 7-layer silica structure."
  valid_until: null
```

The sandbox's two old fuzzy events (batch cycle variance at cycle 7; delayed Southern Dunes shipment)
expired in May 2026 by their own valid_until dates and are not imported.
