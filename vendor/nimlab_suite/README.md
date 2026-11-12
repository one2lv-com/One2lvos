# NVIDIA NIM test lab

A test lab for NVIDIA NIM API keys, endpoints and model combinations. It checks which endpoints answer, benchmarks them, runs a temporary persona ("Quill", defined in `soul.md`) on top of a set of role models, and now judges models against each other so you can pick the best one for each role by score. It is plain Python 3 standard library with zero external packages, and it runs in Termux on Android.

## Layout

```
start.sh                    TUI launcher (no inline Python; calls the modules below)
nvidia_playground.py        single-model tester, compare mode, inspector, legacy route-guess sweep (--sweep)
nvidia_benchmark_suite.py   embeddings recall, vision, LLM logic, Magpie RTF benchmarks
orchestrator_testbed.py     interactive entity chat: soul.md persona, roles, memory, MCP tools
nvidia_router.py            compatibility shim, re-exports nimlab.router.NvidiaRouter

nimlab/                     shared core used by every tool
  core.py                   HTTP client (timeouts, retries, size caps, error objects), keys, masking, SSE, multipart
  api.py                    NimClient: chat, streaming chat, embeddings, vision, OCR, Magpie TTS
  router.py                 endpoint registry router, model classification, live fleet and judge candidates
  config.py                 paths, atomic JSON writes, config defaults
  store.py                  the data stores in data/: paths, load/save, sync rules, migration (single source of truth)
  defaults.py               built-in routing rules, route matrix and starter config for a fresh install
  picker.py                 the "Verified 200 OK / All discovered" list prompt
  memory.py                 MemoryCore vector store (JSON)
  mcp.py                    hardened MCP client and tool-call pipeline
  entity.py                 the entity (persona + roles + memory + tools), shared by testbed and judge
  judge.py                  model ranking per type and entity scoring
  battery.py                fixed test batteries with ground truth
  assets.py                 generates the bundled test images (stdlib PNG writer)
  cli.py                    `python3 -m nimlab ...` subcommands used by start.sh
  scrape.py                 polite public-page fetcher (browser UA, per-host delays, TTL cache)
  catalog.py                model discovery: site + sitemap + docs + key list -> data/models_discovered.json
  spec.py                   OpenAPI spec extraction from NGC spec JSON, model pages and docs; minimal requests
  sweep.py                  spec-driven sweep: plans, probes, result classes, writes the data stores

assets/                     vision_test.png and ocr_test.png (known answers for the judge)
tests/                      offline unit tests (HTTP is mocked)
tests/fixtures/             real pages saved from build.nvidia.com, docs.api.nvidia.com and NGC (gzipped)
samples/                    two Magpie WAVs from the earlier run (Aria, Jason)
data/                       everything the lab learns (see "Data files"); created on first run
output/                     generated files only: WAVs, page/spec caches

config_cluster.json         roles, HTTP, voice, MCP, memory and judge settings (recreated if missing)
config_system_prompts.json  system prompt per role (recreated if missing)
soul.md                     the persona (temporary; swap freely)
```

Data goes to `data/` (override with `NIMLAB_DATA_DIR`), generated files to `output/` (override with `NIMLAB_OUTPUT_DIR`). Paths resolve from the project folder, so the tools work no matter which directory you launch them from.

## Data files

All lab data lives in `data/`, read and written only through `nimlab/store.py` (atomic writes; no API key is ever stored). Every file is created with a valid empty structure the first time it is needed, so a fresh unzip with no data starts cleanly, and a deleted file simply comes back empty. A file that is not valid JSON is moved to `data/legacy/corrupt/` and recreated.

| File | One job |
|---|---|
| `endpoints.json` | Every known endpoint URL: method, content type, host, kind, NVCF function id, models using it, sources (registry, matrix, override, spec, sweep, probe), first/last seen, last result. `routing` holds the router's rules (gateways, static routes, prefix rules, NVCF fallbacks, per-model overrides) and `candidate_routes` the route templates the 200 sweep tries. `stale` holds endpoints no longer in use. |
| `models_discovered.json` | Every model from build.nvidia.com (site, sitemap), the docs and the key's `/v1/models`, merged: sources, kind, slug, page/docs links, status (active, deprecated, retired, unlisted), first/last seen. `key_list` is the key's own list. `removed` holds models no source lists any more. |
| `models_verified.json` | Only models whose latest test answered 200 OK: working endpoint, method, request template, latency, when and by which sweep. `dropped` holds models that fell out, with their last result. |
| `benchmark_latest.json` | The most recent benchmark run (a single-track run replaces only its track). |
| `benchmark_history.json` | One-line summaries of the last 10 runs. |
| `probe_results.json` | The last test result of every model ever probed (all statuses) plus its previous 5; `archived` holds models that left discovery. Gives the failing and never-tested lists. |
| `judge_leaderboard.json`, `judge_entity_scores.json` | Judge rankings per role and role-combo scores. |
| `memory.json` | The entity's vector memory. |
| `test_history.jsonl` | The playground's single-test log. |
| `legacy/` | Pre-3.1 files moved here by the migration, and `migrations.json` saying what each run imported. |

Roles, voice profiles, MCP allowlist and judge settings stay in `config_cluster.json` (they are settings, not results). Page and spec caches stay in `output/cache/` because they can be thrown away.

**Lists:** `./start.sh data` prints counts for every store; `./start.sh data show <list>` prints one list: `endpoints`, `stale`, `discovered`, `retired`, `deprecated`, `unlisted`, `removed`, `key`, `verified`, `dropped`, `failed`, `untested`, `benchmarks`. Launcher option L has the same views.

**Sync rule.** New results add what is new and remove what is gone, but a run only removes within what it actually checked:

- Discovery: a model missing from the new data loses only the sources this run read completely; it leaves the list (to `removed`) when no source lists it any more. A source that failed, returned a partial list, or an `--offline` run removes nothing.
- Verified: a 200 adds or refreshes a model; a conclusive failure moves it to `dropped`. Rate limits and plan-only results change nothing. If every failure in a run is an auth error or timeout (bad key, no signal), nothing is dropped. A full sweep (no `--models`, `--kinds`, `--limit`, `--site-only`, `--offline`, not stopped with Ctrl-C) also drops verified models that are no longer discovered or registered anywhere. A partial sweep only touches the models it tested.
- Endpoints: any URL a spec names, a sweep uses, or a probe finds (anything except a guessed URL that answered 404/410) is added; a known one gets `last_seen` and `last_result` updated. Endpoints are never deleted. After a full sweep, one found by sweeps or specs moves to `stale` when no known model uses it any more or it answered 404/410 with no verified model on it. The registry, matrix and override routes are the routing base and never go stale. A stale endpoint comes straight back the next time anything sees it.

**Migration.** The first run of any tool finds the pre-3.1 files (`nvidia_endpoint_registry.json`, `nvidia_endpoints_matrix.json`, `nvidia_inventory.json`, `nvidia_catalog.json`, `nvidia_verified_endpoints.json`, and `output/spec_sweep_results.json`, `benchmark_results.json`, `leaderboard.json`, `entity_scores.json`, `memory_store.json`, `nvidia_playground_history.jsonl`), builds the stores from them, and moves them to `data/legacy/<time>/`. It merges into stores that already exist (newer results win), so copying old files back in and running again loses nothing. `./start.sh data migrate` runs it by hand.

## Setup

```bash
export NVIDIA_API_KEY=nvapi-...      # or NGC_API_KEY
export MCP_API_KEY=...               # only if you use the MCP bridge
chmod +x start.sh
./start.sh
```

In Termux, install `termux-api` (and the Termux:API app) for audio playback; `mpv` also works. Keys are only ever read from the environment. Option 8 in the launcher can persist the NVIDIA key to `~/.nimlab_env` (owner-only permissions, sourced from `~/.bashrc`) and also removes old plain-text `export NVIDIA_API_KEY=` lines the previous launcher wrote.

## Running each piece

| What | Command |
|---|---|
| Dashboard | `./start.sh` |
| Playground | `python3 nvidia_playground.py` |
| Discover models | `./start.sh discover` (launcher option D) |
| Show catalog / gaps | `./start.sh discover --show --flag on_site_not_in_key` |
| 200 Health & Fallback Sweep (registered endpoints, then scraped spec) | `./start.sh sweep200` (launcher option 2) |
| Spec-driven sweep | `./start.sh sweep` (launcher option S) |
| Sweep some kinds | `./start.sh sweep --kinds chat,vision,embedding` |
| Read specs only | `./start.sh sweep --plan-only` |
| Benchmark suite | `python3 nvidia_benchmark_suite.py` |
| Entity testbed | `python3 orchestrator_testbed.py` |
| Fleet table | `./start.sh fleet` |
| Data stores and lists | `./start.sh data`, `./start.sh data show failed` (launcher option L) |
| Benchmark report | `./start.sh report` |
| Magpie TTS | `echo "hello" \| ./start.sh tts --voice Magpie-Multilingual.EN-US.Jason` |
| Key status (masked) | `./start.sh status key` |
| Judge | `./start.sh judge rank`, `judge entity`, `judge show`, `judge apply` |
| Tests | `python3 -m unittest discover -s tests -t .` |

**Choosing the model list.** Every model menu in the playground (browse, search, test, inspect, compare, code snippet) and the testbed's role hot-swap first asks `1. Verified 200 OK (38)  2. All discovered (243)`. Enter takes the verified list (or the full list when nothing is verified yet). You can still test or assign a model from the full list that has not passed the 200 test; it shows a short note first.

`./start.sh <anything>` passes straight through to `python3 -m nimlab <anything>`.

Testbed chat commands: `/image <path> [prompt]`, `/ocr <path>`, `/deep`, `/code`, `/remember`, `/recall`, `/forget <id>`, `/tools`, `/clear`, `/exit`.

## The judge

### Per-type model ranking

`./start.sh judge rank` (or launcher option 9) runs a fixed battery for each type and builds a leaderboard. Candidates come from `data/models_verified.json`, classified by id and sweep kind; the model currently in the role is always included.

| Type (role) | Objective metric | Judge rubric |
|---|---|---|
| chat (main_brain) | format and length constraints passed | helpfulness, accuracy, instruction following, clarity |
| deep_reasoning | known answers from a `FINAL:` line | reasoning quality, clarity |
| coding (coding_agent) | generated code run against hidden tests | correctness, quality |
| vision | questions with known answers on `assets/vision_test.png` | none |
| ocr (ocr_document) | character error rate on `assets/ocr_test.png` | none |
| embeddings (embedding) | recall@1, recall@3 and MRR on a labeled set | none |
| compactor | key facts kept within a word limit | faithfulness, coverage, concision |
| tts (voice profile) | valid WAV rate and real-time factor | none |

The final score (0 to 100) blends the objective and judge parts by type (see `BLEND` in `nimlab/judge.py`), plus 10% for relative speed (median latency; real-time factor for TTS). Latency and tokens per second are recorded for every model.

Generated code runs in a subprocess with `python3 -I -S`, in an empty temp directory, with an environment that holds no API keys, CPU, file-size and memory limits where the OS allows, and a timeout. Code that imports os, subprocess, socket and similar, or calls open, eval or exec, is refused before it runs. That is a guard rail, not a full sandbox; turn it off with `--no-exec` or `execute_generated_code: false`.

Bias controls:

- Responses are shown to judges under shuffled labels (A, B, C), with model and vendor names redacted from the text.
- The run order of candidates is shuffled too.
- A judge never scores its own model's output.
- Several judges and repeats are averaged (`judges`, `repeats`).
- The judge prompt tells the judge to treat responses as untrusted data, and its JSON output is parsed strictly: an incomplete or out-of-range score is dropped, not guessed.
- The random seed is saved with every result, so `--seed` reproduces a run.

Results go to `data/judge_leaderboard.json` and print as one table per type. `./start.sh judge apply` shows each proposed role change and writes the winners into `config_cluster.json` only after you answer yes (`--types` limits it; the TTS winner goes to `voice_settings.voice_name`).

Useful flags: `--types chat,coding`, `--judges a/model,b/model`, `--repeats 2`, `--max-candidates 6`, `--seed 42`, `--no-exec`.

### Entity scoring

`./start.sh judge entity` runs a fixed persona battery (seven prompts across main brain, deep reasoning and coding) through each role combo in `judge_settings.entity_combos`, with tools off and memory off so runs are comparable. Judges score every reply against `soul.md` on:

- **in_character** (30%): identity, temperament, stance
- **voice_rules** (25%): short paragraphs, sharp sentences, no hedging, never apologetic
- **clarity** (20%)
- **task_quality** (25%)

A combo's score is the mean rubric score times its completion rate, so a combo that times out on some prompts ranks lower. Results go to `data/judge_entity_scores.json`. Pass `--combos my_combos.json` to test other combos without editing config.

## Config options (config_cluster.json)

Missing keys fall back to the defaults in `nimlab/config.py`, so older configs keep working.

**http_settings**: `timeout_sec` (60), `retries` (2, on 429/5xx and network errors, honoring Retry-After), `backoff_sec` (1.5).

**voice_settings**: `voice_name`, `auto_tts`, `language`, `tts_url` (the Magpie NVCF function URL, also `NIMLAB_TTS_URL`), `voice_profiles` (the TTS candidates for the judge).

**mcp_settings**:

- `enabled`, `url`
- `auth.style`: `x-api-key` (default, for svn-dev.online), `bearer`, `header` (custom `auth.header_name`) or `none`
- `auth.key_env`: env var holding the key (default `MCP_API_KEY`). The key is never stored in config.
- `protocol_version` (2025-06-18; the server's answer is used after initialize)
- `allowed_tools`: tool names the model may run; `["*"]` allows every advertised tool. **Empty (the default) means no tools are offered or run.**
- `confirm_tool_calls` (true): ask y/N in the terminal before each call
- `max_tool_steps` (4), `max_calls_per_step` (3)
- `tool_timeout_sec` (20), `max_result_chars` (8000), `max_response_bytes` (1,000,000)

**memory_settings**: `recall_top_k`, `similarity_threshold`.

**judge_settings**:

- `judges`: judge model ids
- `repeats` (1), `judge_temperature` (0.0)
- `max_candidates_per_type` (16; above this a reproducible random sample is taken, current role model kept)
- `execute_generated_code` (true), `code_timeout_sec` (10)
- `entity_combos`: `[{"name": ..., "roles": {role: model}}]`; roles not listed keep their current model
- `candidate_overrides`: `{type: [model ids]}` to replace the auto-picked candidates for a type

## Model discovery (`discover`)

The key's `/v1/models` misses a lot of what build.nvidia.com shows (speech, CV, image generation, many partner and new models) and still lists models the site has retired. `discover` builds one catalog from four public sources, none of which needs a key:

1. **Site**: the NGC catalog search API that build.nvidia.com/models itself calls (`api.ngc.nvidia.com/v2/search/catalog/resources/ENDPOINT`, org `qc69jvmznzxy`). The exact query is read from the live /models page so the list matches the site; a built-in copy is the fallback. Gives slug, publisher, labels, playground type and the `DEPRECATION` date.
2. **Sitemap**: `build.nvidia.com/sitemap.xml`, the fallback list of model pages if the search API fails.
3. **Docs**: the sidebar of `docs.api.nvidia.com/nim/reference`, whose titles carry exact API ids with dots (`moonshotai / kimi-k3.1-pro`), the category and a deprecated flag. Fallback: the docs sitemap.
4. **Key**: the live `/v1/models` (when a key is set) or the key list saved in `data/models_discovered.json`.

Each model gets `id` (API model id), `publisher`, `slug`, `page_url`, `docs_url`, `kind` (chat, vision, embedding, rerank, ocr, tts, asr, translation, image_gen, video, cv, safety, biology, simulation), `sources`, `status` (active, deprecated, retired, unlisted) and `flags` (`on_site_not_in_key`, `in_key_not_on_site`, `deprecated`, `retired`). Slugs write dots as underscores (`kimi-k3_1-pro` is `moonshotai/kimi-k3.1-pro`); a few use dashes (`glm-5-3-flash`), so ids are matched loosely across sources and the docs or key spelling wins.

Each run syncs into `data/models_discovered.json` (see "Data files"). The playground's full list and the sweep read it; the judge uses the catalog kind to keep safety, biology and similar models out of chat leaderboards.

## Spec-driven sweep (`sweep`)

For each model the sweep finds its API definition, in this order:

1. `api.ngc.nvidia.com/v2/endpoints/qc69jvmznzxy/<slug>/spec`: the JSON record build.nvidia.com renders the model page from. It holds the full OpenAPI spec (servers, paths, request schemas, examples), the NVCF function id, `nvcfInferencePath` (`/grpc` for gRPC-only models), the code samples and the deprecation notice. 20 to 50 KB a model.
2. The model page itself (`build.nvidia.com/<publisher>/<slug>`), where the same spec is embedded in the Next.js stream. Only used if the spec API errors.
3. The docs reference page `docs.api.nvidia.com/nim/reference/<publisher>-<slug>-infer`.

From the spec it derives the exact URL and request: `integrate.api.nvidia.com/v1/...` for chat, embeddings and rerank, `ai.api.nvidia.com/v1/cv/...` and `/genai/...` for vision, OCR and image models, the NVCF function host (`https://<function-id>.invocation.api.nvcf.nvidia.com/v1/audio/synthesize`, multipart, `function-id` header) for Magpie TTS and the ASR models, and `api.nvcf.nvidia.com/v2/nvcf/pexec/functions/<id>` as a second route for self-hostable CV specs. The probe body is the smallest request that satisfies the schema (8 output tokens, no streaming, a 16x16 test PNG where an image is required); if that is rejected as a bad payload, the page's own example is tried. Only models with no spec anywhere fall back to the old route guessing.

Result classes:

| Class | Meaning |
|---|---|
| `LIVE_200` | 2xx from the exact endpoint (202 counts: NVCF accepted it) |
| `NEEDS_DIFFERENT_PAYLOAD` | 400/405/415/422; `reason` holds the server's schema hint |
| `AUTH_OR_ENTITLEMENT` | 401/403, or NVCF "function not found for account": the key cannot use it |
| `RETIRED_OR_DEPRECATED` | page notice says support ended, or 404/410 on every route |
| `GRPC_NVCF_ONLY` | the model is only served over gRPC (`grpc.nvcf.nvidia.com:443`); not probed |
| `TIMEOUT_OR_SERVER_ERROR` | timeout, network error or 5xx |
| `RATE_LIMITED` | 429 after retries |
| `NO_HOSTED_API` / `NO_WORKING_REST_ENDPOINT` | no hosted API on the page / no spec and every guess failed |
| `SPEC_FOUND_NOT_PROBED` | plan-only run, or no key set |

A probing run syncs into the data stores: 200 OK models into `models_verified.json` (keyed by the exact API model id, so the router, fleet table and judge pick them up), every result into `probe_results.json`, every endpoint into `endpoints.json`, and each spec-derived route into `routing.explicit_model_overrides`, which the router honours with the exact URL, method, content type and function id. A plan-only run records the spec endpoints and changes nothing else. By default the sweep covers every discovered model plus every model the endpoint registry or verified list names.

Politeness: browser-like User-Agent, one request at a time per host with a minimum gap (10 s for build.nvidia.com as its robots.txt asks, 3 s for docs, 1 s for the NGC API), up to 3 probe workers against the API hosts, and caches with a 72-hour TTL (`output/cache/pages` for catalog sources, `output/cache/specs` for extracted plans; raw model pages are not kept). The API key is only sent to the API hosts, never to the public pages, and is never written to logs, results or caches; error text is passed through a redactor that masks anything key-shaped.

**discovery_settings** in `config_cluster.json`: `page_ttl_hours` (72), `spec_ttl_hours` (72), `probe_workers` (3), `probe_timeout_sec` (20), `host_delays_sec`, `include_retired_in_sweep` (false), `playground_uses_catalog` (true). `--refresh` ignores caches, `--offline` uses caches only, `--fast` shortens the page delays.

## MCP flow

The testbed talks to the MCP server over Streamable HTTP: `initialize`, then `notifications/initialized`, then `tools/list` (with paging), then `tools/call`. It accepts JSON or SSE responses and carries `Mcp-Session-Id` and `MCP-Protocol-Version` forward. A model's tool call must be strict JSON:

```
<tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>
```

The older `<tool_call name="...">{...}</tool_call>` form is still accepted. Each call is checked in order: it must parse, the tool must have been advertised by the server, the arguments must match its `inputSchema`, it must be on the allowlist, and you must confirm it. Anything that fails is reported back to the model as a rejected call and nothing runs. Results come back to the model fenced as untrusted data, truncated to the size limit, with any tags inside them neutralized.
