# Changes

## v3.2.0
- **16 settable roles** in the testbed: Intent Router / Fast Dispatcher, Conversational Persona LLM, Agentic Long-Context & Reasoning, Coding & Tool-Calling, Vision-Language (VLM), Document & Structured OCR, Chart & Plot Parser, Video & Temporal Understanding, ASR / STT, Omni-Modal Audio-Language, Neural TTS, Text-to-Image, Audio / Music Generation, Dense Text & Multimodal Embedding, Semantic Reranker, Translation & Guardrail. Old role names migrate automatically (config backed up to `data/legacy/`).
- **Model or MCP tool per role.** Each role is backed by a model endpoint or a tool from the connected MCP server (picked from tools/list, with automatic argument mapping you can edit). Menus and the launcher header show the backend type.
- **Routing:** the intent router sends each chat turn to the right role; memory recall can be re-sorted by the reranker; optional guardrail check and a translate command; image, audio and music outputs save to `output/`.
- **Voice cloning** for the TTS role when the model supports it (magpie-tts-zeroshot / flow, or any spec with `audio_prompt`): attach a 3-10 s reference clip from your phone (path checked, stereo/sample rate/length fixed automatically, other formats need ffmpeg), plus a transcript when the model needs one. Sent as the `audio_prompt` multipart field, or mapped to an MCP tool's reference-audio argument. Shown as "cloned voice: <file>".
- **Test a role:** sends a small probe to any role's backend and shows status and latency. Launcher menu R views and changes roles.
- Not yet checked live: the magpie-tts-flow model name and transcript requirement, and the zero-shot function id (taken from a saved spec).
- 254 offline tests pass (57 new in `tests/test_roles.py`).

## v3.1.0
- **Data reorganized into `data/`**, one job per file, all read and written through the new `nimlab/store.py` (atomic writes, no API key ever stored): `endpoints.json` (every endpoint URL + the router's rules + route templates), `models_discovered.json` (site, sitemap, docs and key, merged), `models_verified.json` (only the current 200 OK fleet), `benchmark_latest.json` + `benchmark_history.json` (last 10 runs), plus homes for the lists the lab already kept or needed: `probe_results.json` (last result of every model probed; gives the failing and never-tested lists), `judge_leaderboard.json`, `judge_entity_scores.json`, `memory.json`, `test_history.jsonl`. Retired/deprecated models are a status in the discovered list and have their own view.
- **Missing files are created.** Every store is created with a valid empty structure on first use; `config_cluster.json` and `config_system_prompts.json` are recreated with the starter settings if missing. A fresh unzip with no data files starts cleanly; a corrupt store is moved to `data/legacy/corrupt/` and recreated.
- **One-time migration**: the first run builds the stores from the old `nvidia_*.json` files and the old `output/` results (verified entries, overrides, catalog, key inventory, route matrix, spec sweep results, latest benchmark, leaderboard, entity scores, memory, history), then moves the old files to `data/legacy/<time>/`. `./start.sh data migrate` runs it by hand; it merges, so a second run loses nothing.
- **Sync rule**: new results add what is new and remove what is gone, only within what the run covered. Discovery removes a model only when every source that listed it was read completely and no longer lists it. Verified: pass adds, conclusive failure moves to `dropped` (rate limits, plan-only and all-auth/timeout runs drop nothing); a full sweep also drops models no longer known anywhere. Endpoints are added whenever a spec, sweep or probe finds them and are never deleted: after a full sweep, sweep/spec endpoints no model uses move to `stale` and return when seen again. Every removed record keeps its last state (`removed`, `dropped`, `stale`, `archived`).
- **List prompt**: playground browse, search, test, inspect, compare and code-snippet menus, and the testbed's role hot-swap, ask `1. Verified 200 OK (N)  2. All discovered (M)` (default verified). Testing or assigning an unverified model from the full list shows a short note.
- Sweeps record every spec endpoint and every probed URL that exists; the 200 sweep and spec sweep both sync verified, probe results and endpoints. Stopping the 200 sweep with Ctrl-C saves what it tested.
- New `./start.sh data` (counts) and `./start.sh data show <list>` (endpoints, stale, discovered, retired, deprecated, unlisted, removed, key, verified, dropped, failed, untested, benchmarks); launcher option L. Status header shows verified, discovered and endpoint counts.
- Benchmark: running one track saves it into the latest benchmark (other tracks kept) instead of discarding it.
- Tests run against a throwaway data folder, never your real `data/`.

## v3.0.4
- Every model list and picker shows only models that passed the 200 test (LIVE_200 in nvidia_verified_endpoints.json). The sweeps still probe every known model.
- Playground: browse, search, test, inspect and compare list only 200-tested models; the header shows "200-tested: N (of M known)". Syncing /v1/models or running discover adds to what the sweeps probe, not to the lists. Lists refresh after a sweep.
- Benchmark: the inventory and hardcoded 21-model fallbacks are gone; with no 200-tested models it says to run the sweep.
- Orchestrator: the role hot-swap only accepts 200-tested models, and the main menu marks any assigned role that hasn't passed.
- Judge: candidate overrides and the current role model are only included when they passed the 200 test.

## v3.0.3
- Benchmark suite covers every LIVE_200 endpoint. It only had three scored tracks (reasoning, vision, embeddings), so safety/guard, translate, OCR/parse, rerank, CV, image generation and speech models were silently dropped. Those now go to a new smoke track (menu option 6, also part of option 5) that re-probes each one with its saved URL, method, content type, function id and request, and reports status and latency.
- The menu shows a coverage line (live total = reasoning + vision + embedding + smoke-tested) so a gap is visible. Classification now uses the catalog kind from the sweep, and a model only enters the chat/vision tracks when its endpoint is chat/completions.
- The report JSON gains other_smoke and coverage. New tests: tests/test_benchmark_coverage.py.

## v3.0.2
- The 200 Health & Fallback Sweep now runs in two stages for each model. Stage 1 tries every endpoint the JSON files register for it: its entry in nvidia_verified_endpoints.json, the registry (explicit override, prefix rule or static route), the default path for its kind, then every route in nvidia_endpoints_matrix.json. Stage 2, only when none of those answer 200, reads the model's scraped API spec (NGC spec JSON, then the build.nvidia.com page, then docs), fetching it when it isn't cached, and probes the exact endpoint it names.
- The model list now also includes every model registered in the verified endpoints file and the registry overrides.
- Failures get the finer result classes (auth/entitlement, needs a different payload, retired, rate-limited, no hosted API, gRPC only) instead of a blanket FAILED, with the reason saved.
- Results now merge into nvidia_verified_endpoints.json instead of overwriting it, and spec routes that work are added as router overrides. The summary shows how many models the scraped spec rescued.
- Two prompts at the start: whether to check scraped specs, and whether to fetch specs that aren't cached (answer no for a fast, cache-only run).
- Probes go through the shared nimlab prober, so NVCF multipart speech endpoints with a function id are tested properly. New tests: tests/test_sweep200.py.

## v3.0.1
- The classic 200 Health & Fallback Sweep is back on the main menu as option 2, and runs directly with `./start.sh sweep200`. It is unchanged from the original and still writes nvidia_verified_endpoints.json.
- The spec-driven sweep moved to launcher option S (`./start.sh sweep` is unchanged). The playground's sweep option now defaults to the 200 sweep.

## v3.0.0
- New `discover` subcommand (launcher option D): merged model catalog from the build.nvidia.com search API (the one /models uses), build.nvidia.com sitemap, docs.api.nvidia.com reference index and the key's /v1/models. Writes nvidia_catalog.json with id, publisher, slug, page/docs URLs, kind, sources, status and flags (on_site_not_in_key, in_key_not_on_site, deprecated, retired).
- New spec-driven `sweep` (launcher option 2): reads each model's spec from the NGC endpoint spec JSON, falling back to the model page HTML, then the docs reference; probes the exact URL (integrate, ai.api cv/genai, NVCF function host with function-id, pexec) with a minimal schema-valid request; retries with the page example on a payload error; route guessing only when no spec exists.
- New result classes: LIVE_200, NEEDS_DIFFERENT_PAYLOAD, AUTH_OR_ENTITLEMENT, RETIRED_OR_DEPRECATED, GRPC_NVCF_ONLY, TIMEOUT_OR_SERVER_ERROR, RATE_LIMITED, NO_HOSTED_API, NO_WORKING_REST_ENDPOINT, SPEC_FOUND_NOT_PROBED.
- Results merge into nvidia_verified_endpoints.json (keyed by exact API id) and explicit_model_overrides in the registry; the router honours exact override URLs, content type and function id.
- Playground model list includes catalog models and drops retired ones; judge candidate types use the catalog kind.
- New nimlab/scrape.py (polite fetcher: browser UA, per-host delays incl. robots.txt crawl-delay 10 s, TTL cache, stale fallback), catalog.py, spec.py, sweep.py. Multipart builder supports file parts. Redactor masks any key-shaped string.
- tests/test_discovery.py plus real saved pages in tests/fixtures.


This maps each item on your list, plus the fixes found on review, to what was done. Version 2.0.0.

## 4. start.sh security

**Problem:** the launcher spliced the API key and typed speech text straight into inline `python3 -c` source (`'${NVIDIA_API_KEY}'`, `'''${user_phrase}'''`). A quote in the phrase broke it, and a crafted phrase could run code.

**Done:**

- All inline Python is gone from `start.sh`: no `python3 -c`, no heredocs. Each block became a real subcommand in `nimlab/cli.py`: `status`, `fleet`, `report`, `tts`, `persist-key`, `forget-key`, `judge`.
- Data moves only through env vars, argv and stdin. The TTS phrase goes in over stdin (`printf '%s' "$phrase" | nimlab tts --voice "$voice"`), and the key is read from the environment inside Python.
- Every shell variable is quoted. `read -r` throughout, and the key prompt uses `read -s` and strips CR/LF, quotes and spaces.
- The key is displayed masked only (`nvapi-...WXYZ`).
- Persisting the key no longer appends a plain `export NVIDIA_API_KEY=...` to `~/.bashrc`. It writes `~/.nimlab_env` with owner-only (600) permissions, shell-quoted, sources it from `.bashrc` with one line, and removes the old plain-text export lines. "Clear key" removes both.
- The script runs from any directory (it `cd`s to its own folder), and `./start.sh <command>` runs one CLI command without the menu.
- New menu option 9 opens the judge.
- **shellcheck 0.11.0 reports no findings.**
- Tests: a hostile phrase containing `'''`, `$(...)` and backticks goes through menu option 7 and creates no marker file; a key containing `'`, `"`, `$(id)` and backticks round-trips through persist-key exactly and never prints.

Also fixed in the same spirit: the playground's "OpenAI snippet" printed your real key into the snippet. It now reads `os.environ["NVIDIA_API_KEY"]`.

## 5. Orchestrator MCP hardening

**Problem:** tools were advertised to the model, but calls were parsed with a loose regex and run without checks. Only one tool call per turn was handled (a second went nowhere). There was no MCP handshake, and the bridge sent `Authorization: Bearer` with an empty key while your server checks `X-API-Key`.

**Done (new `nimlab/mcp.py`):**

- **Protocol:** `initialize`, then `notifications/initialized`, then `tools/list` (with cursor paging), then `tools/call`, as JSON-RPC 2.0 over Streamable HTTP. JSON and SSE responses are both handled; server notifications in the stream are skipped; `Mcp-Session-Id` and the negotiated `MCP-Protocol-Version` are sent on later requests; an expired session (404) is reported.
- **Auth:** `mcp_settings.auth.style` is `x-api-key` (default, matches svn-dev.online), `bearer`, `header` (custom name) or `none`. The key comes from `MCP_API_KEY` (or any env var named in `auth.key_env`) at call time and is never stored in config. With no key set, no auth header is sent, never an empty Bearer. A 401 or 403 says to check `MCP_API_KEY`.
- **Parsing:** strict JSON body `{"name", "arguments"}` only. Not-JSON, non-object bodies, extra keys, bad names, non-object arguments, odd tag attributes, nested and unclosed tags are all rejected. The legacy `name="..."` form is still accepted when its body is strict JSON.
- **Validation:** the tool must be one the server advertised. Arguments are checked against its `inputSchema`: required fields, types (a bool is not an integer), enum, string length, numeric range, array size and items, `additionalProperties: false`, nested objects.
- **Policy:** `allowed_tools` in config (empty by default, so tools are opt-in; `"*"` allows all) plus a y/N prompt before every call (`confirm_tool_calls`, on by default). Only allowlisted tools are described to the model.
- **Limits:** per-call timeout (`tool_timeout_sec`), response byte cap (`max_response_bytes`, applied to JSON and SSE), result text cap (`max_result_chars`).
- **Untrusted results:** results go back inside `<tool_result ... trust="untrusted">` with BEGIN/END markers and a note that the content is data, not instructions. Any `<tool_result>` or `<tool_call>` tags inside a result are neutralized, so a result cannot fake a tool call. Known secrets are redacted.
- **Loop:** bounded multi-step loop (`max_tool_steps`, default 4; `max_calls_per_step`, default 3). Rejected, declined and failed calls are reported back to the model so it can recover, and nothing is executed for them.

## 6. Duplicated responsibilities

**Problem:** the playground, benchmark suite, launcher and orchestrator each had their own urllib code, key loading, endpoint handling and Magpie multipart builder.

**Done:**

- New `nimlab/` package is the one shared core:
  - `core.py`: `HttpClient` with timeouts, retries with backoff on 429/5xx and network errors (honors Retry-After), response size caps, and one `HttpResult` error object (`ok`, `status`, `error_kind`: http, timeout, network or too_large). Also key loading (`NVIDIA_API_KEY`, then `NGC_API_KEY`), masking, redaction, SSE parsing, and multipart with a random boundary.
  - `api.py`: `NimClient` with chat, streaming chat, embeddings (retries without `input_type` when a model rejects it), vision, OCR, Magpie TTS over NVCF multipart, and WAV helpers. Every call returns a `ModelResult`.
  - `router.py`: the registry router (moved from `nvidia_router.py`, which is now a one-line shim), model classification, the live fleet and judge candidates.
- `orchestrator_testbed.py` is now only the interactive front end over `nimlab.entity`, and dropped from about 580 lines to about 300.
- `nvidia_playground.py` and `nvidia_benchmark_suite.py` keep their menus and behavior, but every request goes through `nimlab.core.HttpClient`.
- `start.sh` calls `python3 -m nimlab`.
- A test asserts that no top-level script imports urllib directly.
- `patch_orchestrator_voice.py` is deleted. Its change (Magpie TTS through the NVCF multipart endpoint, with playback through termux-media-player) now lives in `NimClient.tts` and `play_audio`, used by the testbed's `auto_tts`, launcher option 7, the playground (Magpie models are routed to NVCF) and the judge.
- The benchmark suite now classifies models with the same rules as the judge and reads the WAV header for audio duration instead of assuming 22.05 kHz.

## Extra fixes found on review

- **Errors stored as memories:** `MemoryCore.store` refuses empty and error text (`[ERROR ...]`, `[VISION ERROR ...]`, and turns whose reply is an error), and the testbed only stores a turn when the call succeeded. A failed turn is also removed from chat history. On load, existing error records are dropped and the file is rewritten.
- **The existing error record:** the old `memory_store.json` had two records, and both were the same failure (`[ERROR None]: The read operation timed out`), for "hi there" and "hi". Neither is kept. The store starts empty in `output/` on first run.
- **Memory ID collisions:** ids are now random UUIDs (`mem_<hex>`), so deletions can never cause a collision. A `/forget <id>` command was added. Records also carry `embed_model` and `dims`; recall skips vectors from a different embedding model instead of comparing mismatched vectors.
- **Atomic writes:** all JSON writes (config, memory, verified fleet, reports) are atomic.
- **Secrets in history:** playground history lines are redacted before they are written.

## Added: judge model

`nimlab/judge.py`, `nimlab/battery.py` and `nimlab/assets.py`, plus launcher option 9 and `python3 -m nimlab judge {rank,entity,show,apply}`. The README covers the batteries, metrics, rubrics, blend weights, bias controls, the code sandbox and the config keys.

- Test images are generated with the standard library, so vision and OCR have exact ground truth.
- Winners are written to `config_cluster.json` only after you confirm.

## Generated outputs

- Removed from the project: the WAVs, `nvidia_playground_history.jsonl`, `memory_store.json` and `image.png`. All new output goes to `output/`.
- Two Magpie WAVs (Aria and Jason) are kept in `samples/`.
- The playground history was dropped: it held five test calls from the earlier run, four of which failed (one 404, three timeouts).

## Verification (no live key available)

- `py_compile` and pyflakes are clean on every file.
- shellcheck reports no findings on `start.sh`.
- 89 unit tests in `tests/` pass. They mock HTTP and cover the core client, NimClient, MCP parsing, validation, policy, the JSON-RPC/SSE flow and the tool loop, memory, the router, judge metrics and scoring, the rankers end to end with fake models, and offline launcher paths.
- Nothing was tested against the live NVIDIA or MCP endpoints.
