# NVIDIA NIM test lab

A test lab for NVIDIA NIM API keys, endpoints and model combinations. It checks which endpoints answer, benchmarks them, runs a temporary persona ("Quill", defined in `soul.md`) on top of a set of role models, and now judges models against each other so you can pick the best one for each role by score. The core is plain Python 3 standard library (optional packages add gRPC speech models and Oracle memory). It runs in Termux on Android and on a Linux VPS such as an Oracle Cloud Always Free micro instance.

**Start with the menu:** `./start.sh` (or `nimlab` once the shortcut is installed) opens the launcher; every feature is a key on it, and each screen offers the next step. **Updating:** unzip the new release over this folder, then `bash update.sh` (see [Updating](#updating-updatesh-v382)).

**Quick links:** [Command reference](#command-reference) (every command, grouped; also `nimlab commands`) · [Tests](#tests-v374) (`nimlab test`) · [Troubleshooting](#command-reference) (`nimlab troubleshoot`) · [Deploy on a Linux VPS](#deploy-on-a-linux-vps-oracle-cloud-always-free)

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
  roles.py                  the 16 role types, their backends (model or MCP tool) and role specs
  server.py                 OpenAI-compatible test server (routes, auth, SSE, request log, tunnel, self-test)
  servemenu.py              the test server's menus and `serve` command
  wizard.py                 guided setup (`nimlab setup`, 11 steps)
  setupflow.py              setup data checks, role suggestions, embedding choices (v3.7.2)
  configlint.py             flags homepage speech URLs and bare-URL roles (v3.7.2)
  routerbench.py            router benchmark: the chat/call pipeline timed (v3.7.2)
  tunnel.py                 Cloudflare quick / named tunnel, install, keeper with retries
  service.py                keep-running service: termux-services, systemd user unit, built-in supervisor
  telegram.py               Telegram bot connector (polling or webhook)
  selfadmin.py              self-admin tools for the testbed entity (admins only, undo, audit log)
  shortcut.py               the `nimlab` command

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
| `server_settings.json` | The test server's settings and its generated API key (owner-only file; see "OpenAI-compatible test server"). |
| `server_requests.jsonl` | The test server's request log: time, method, route, model, status, latency, error. Keys are masked. |
| `legacy/` | Pre-3.1 files moved here by the migration, and `migrations.json` saying what each run imported. |

Roles, voice profiles, MCP tool overrides and judge settings stay in `config_cluster.json` (they are settings, not results). Page and spec caches stay in `output/cache/` because they can be thrown away.

**Lists:** `./start.sh data` prints counts for every store; `./start.sh data show <list>` prints one list: `endpoints`, `stale`, `discovered`, `retired`, `deprecated`, `unlisted`, `removed`, `key`, `verified`, `dropped`, `failed`, `untested`, `benchmarks`. Launcher 6 Roles & data, option 4, has the same views.

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

**Guided setup (v3.7.2).** The easiest start is `./start.sh setup` (or `nimlab setup`, or **S** on the launcher; it is also offered once on first launch). The NVIDIA key comes first, then everything the key can reach is found and tested before anything is built on it: discovery, the model pages (function IDs and specs), the 200 OK test, MCP, then roles chosen from what actually answered, then the rest. Each step shows its status, then lets you run it, skip it or quit; after a step it shows the new status and offers to run it again. It ends with a summary of what works and what is left.

| # | Step | What it does |
|---|---|---|
| 1 | key | NVIDIA key, typed hidden, checked against NVIDIA, saved to `~/.nimlab_env` (600) or kept for this run. Right after it, quietly: missing dependencies (`pkg install python-grpcio ffmpeg` on Termux, then `nvidia-riva-client`, `oracledb`) and the `nimlab` shortcut |
| 2 | discover | every model on the key (API catalog) plus build.nvidia.com and the docs, with progress (`nimlab discover`; up to 20 minutes) |
| 3 | functions | reads each model's build.nvidia.com page and spec: endpoints, gRPC-only marks, NVCF function IDs, samples. No test requests (`sweep --plan-only`, then `grpc fill`; up to 25 minutes) |
| 4 | sweep | the 200 OK test: one small request per model; writes `models_verified.json` and `probe_results.json` (with the `GRPC_NVCF_ONLY` marks) and fills any gRPC function ID still missing. Full (up to 45 minutes), faster (build.nvidia.com models only, shorter waits, up to 12 minutes) or skip |
| 5 | mcp | MCP URL, key (sent on stdin, never on a command line) and auth style, then a live test |
| 6 | roles | one suggestion per role from the 200 OK list and the MCP tools (an MCP tool for MCP-capable roles such as TTS or image generation); accept them all, change one (numbered list of suited and possible models and tools, or type an id), or keep the current ones |
| 7 | grpc | reports the gRPC-only models and their function IDs (collected in steps 3 and 4); look up missing ones, check them, or paste one |
| 8 | memory | Oracle (TLS connection string or a wallet folder; written to `~/.config/nimlab/oracle_mem.json`, 600), ORDS, a local folder, or off; then embeddings (the recommended model plus the embedding models that passed the 200 OK test, each with its size against the VECTOR(2048) table), `memory test` and `memory setup` |
| 9 | server | server settings, a local self-test, then tunnel and keep-running (below) |
| 10 | telegram | bot token, owner capture, polling or webhook, voice replies |
| 11 | selfadmin | turn self-admin on, the admin key, the shell switch |
| 12 | audio | optional, Skip by default: register a phone for the audio bridge and print its ready-to-paste Termux block; loops for more phones (`nimlab setup phone`) |

A step whose data comes from an earlier step that was skipped says so plainly, for example "No models discovered yet, so there is nothing to test: run step 2 (Discover models)", and offers to run that step now. It never blames the key or the internet for missing data. Ctrl+C during a long step stops that step only (what it finished is kept) and setup goes on. On an existing install (models, specs and roles already there), the data steps show their status with **Skip** as the default and offer "Run discovery again (refresh)" instead of forcing it. Setup and `nimlab doctor` also flag settings that look set but cannot work: a `voice_settings.tts_url` that is a website homepage (for example `https://nvidia.com`) instead of a speech endpoint, and role models or fallbacks that are bare URLs.

`nimlab setup <step>` runs one step (names, the number, or aliases: `catalog` for discover; `specs`, `pages`, `function-ids` for functions; `200`, `200ok`, `probe`, `verify` for sweep; `ltm`, `bot` ...). `nimlab setup deps` and `nimlab setup shortcut` still run on their own, `nimlab setup tunnel` and `nimlab setup service` run just those parts of step 9, and `nimlab setup list` lists the steps in this order.

**Rerun just the new steps on an existing install:** `nimlab setup discover`, `nimlab setup functions`, `nimlab setup sweep`, then `nimlab setup roles` (and `nimlab setup grpc` to review the function IDs). Each one keeps what is there unless you choose to refresh or change it.

**Shortcut.** `./start.sh shortcut` installs a `nimlab` command, so `nimlab` (the dashboard) or `nimlab grpc check`, `nimlab memory test` and any other command work from any folder. See "The nimlab shortcut" below.

In Termux, install `termux-api` (and the Termux:API app) for audio playback; `mpv` also works. Keys are only ever read from the environment. Launcher **7 Keys & MCP**, option 2, can persist the NVIDIA key to `~/.nimlab_env` (owner-only permissions, sourced from `~/.bashrc`) and also removes old plain-text `export NVIDIA_API_KEY=` lines the previous launcher wrote.

## Menus

Every screen follows the same rules: options are numbered 1-9 (the data lists go to 13), **0** goes back, related options sit under a short heading, and the most used ones come first. Lines fit the screen: on a narrow phone (under about 56 columns) the grey hints after each option are dropped and separators shrink to the screen width. Every option runs a command, so everything in the menus also works as `./start.sh <command>`.

**Launcher** (`./start.sh` or `nimlab`), as of v3.8.6 (the banner shows the build version):

| Key | Screen | What is in it |
|---|---|---|
| 1 | Testbed | the entity: chat, voice call, roles, settings (menu below) |
| 2 | Playground | test one model, compare models, inspect |
| 3 | Test server | start (device / LAN / tunnel), connection details, UI configs, self-test, request log, server settings, new key |
| 4 | Discover & sweep | refresh catalog, discovered / unlisted / deprecated lists, spec sweep, 200 health sweep, NVCF gRPC models |
| 5 | Benchmark & judge | run benchmarks, latest report, verified fleet, rankings, leaderboards, apply winners |
| 6 | Roles & data | show the 16 roles, candidates for one, data stores and lists |
| A | Custom endpoints | your own OpenAI-compatible gateways: add, import or type models, put them on roles (see "Custom endpoints") |
| U | Service & update | service status, start, stop, restart, logs, Clean restart (the same steps as `update.sh`) |
| W | Scheduler | scheduler on/off, jobs (list, add step by step, run, pause), heartbeat on/off and "try one now", suggested actions |
| H | Health & repair | quick check, full check, safe repairs (`doctor --fix`, asks first) |
| 7 | Keys & MCP | NVIDIA key (enter, save, clear) and MCP server (URL, key, auth style, test) |
| 8 | Memory | long-term memory: storage, embeddings, behaviour, test, Oracle setup |
| 9 | Tools | install packages, `nimlab` shortcut, voice synthesizer, colours |
| S | Guided setup | the twelve setup steps; the last, a phone for audio, is optional (see "Setup") |
| F | Phone audio bridge | register a phone and print its ready-to-paste Termux block (see "Phone audio bridge") |
| E | Tests | the system tests, one per part, or all of them; history |
| X | Commands & troubleshooting | every command by area (10 to a page; pick one to run it), problems by symptom, the tunnel test |

Result screens end with numbered next steps (for example "Start the scheduler now" after adding a job while it is stopped), so you can go on without typing a command. Colour follows the terminal: off when the output is not a terminal, with `NIMLAB_COLOR=0` or `NO_COLOR`.

The dashboard header also shows the service state (running / stopped / not set up) and the Telegram bot state, and the public URL when a tunnel is up.

The older hidden letter keys still work where they do not clash with the keys above: D discover, G gRPC, B/J benchmark, R roles, L data lists, O server, M/K keys & MCP, Y memory, C colours, V voice synth, I install, N shortcut. (H, W, U, A, E and X now open the screens in the table.)

**Testbed** (`python3 orchestrator_testbed.py`, launcher 1):

| Key | Option |
|---|---|
| 1 | Chat session (text, images, files, `/help`) |
| 2 | Live voice call |
| 3 | Roles: view and hot-swap the 16 roles |
| 4 | Test a role (status and latency) |
| 5 | Voice clone clip for the TTS role |
| 6 | NVCF gRPC models |
| 7 | Settings: 1 MCP server & tools, 2 Voice, 3 Memory, 4 Guard & translate, 5 Routing, 6 Terminal colours. Each group opens its own short screen; changes are saved at once |
| 8 | Test server (runs in the background) |
| 9 | Persona & prompts (soul.md, role prompts) |

**Memory screen** (launcher 8, testbed Settings 3, `./start.sh memory menu`): Storage 1-4 (backend, local folder, Oracle connection, embedding), Behaviour 5-11 (auto store, auto recall, what to save, de-duplication, recall, retention, shared or per user), Check 12-13 (test connection, set up Oracle tables). T and S still run the test and the setup.

**Test server screen** (launcher 3, `./start.sh serve menu`): Run 1-3 (this device, LAN, public tunnel), Use it 4-7 (connection details, UI configs, self-test, request log), Setup 8-9 (server settings, new API key), then G guided server setup (tunnel and service), T tunnel status, K keep-running status, L service log, B Telegram bot, P phone audio bridge.

**gRPC screen** (launcher 4 then 9, testbed 6, `./start.sh grpc menu`): Function IDs 1-4 (paste, refresh, clear, check), Per model 5-6 (language, ASR mode), Try it 7-8 (ASR, TTS).

## The nimlab shortcut

`./start.sh shortcut` (launcher 9 Tools, option 2) installs a small `nimlab` command that runs this folder's `start.sh` with every argument passed through: `nimlab` opens the dashboard, `nimlab grpc check` is `./start.sh grpc check`, `nimlab memory test` is `./start.sh memory test`, and so on, from any folder.

- **Where:** `$PREFIX/bin/nimlab` on Termux (already on your PATH; shebang `$PREFIX/bin/bash`); `~/.local/bin/nimlab` on other Linux (created if missing; it prints the line to add to `~/.bashrc` if that folder is not on your PATH).
- **Why a script, not a symlink:** `start.sh` finds its folder from its own path, which a symlink would point at the bin folder. The wrapper holds the absolute path and runs `exec bash "<folder>/start.sh" "$@"`.
- **Moved the folder?** Run `./start.sh shortcut` in the new place; it updates the path. If the old path is gone, `nimlab` says so instead of failing silently.
- `./start.sh shortcut status` shows where the command is, which `start.sh` it runs, whether that path still exists, and whether another `nimlab` comes first on your PATH.
- `./start.sh shortcut remove` deletes it (only a command this lab made).
- `./start.sh shortcut install <name>` picks another name, e.g. `nim`. A file of that name the lab did not make is left alone with a warning unless you add `--force`. `--dir <folder>` puts it somewhere else.

## Running each piece

| What | Command |
|---|---|
| Dashboard | `./start.sh` |
| Playground | `python3 nvidia_playground.py` |
| Discover models | `./start.sh discover` (launcher 4 Discover & sweep) |
| Show catalog / gaps | `./start.sh discover --show --flag on_site_not_in_key` |
| 200 Health & Fallback Sweep (registered endpoints, then scraped spec) | `./start.sh sweep200` (launcher 4, option 8) |
| Spec-driven sweep | `./start.sh sweep` (launcher 4, option 5) |
| Sweep some kinds | `./start.sh sweep --kinds chat,vision,embedding` |
| Read specs only | `./start.sh sweep --plan-only` |
| Benchmark suite | `python3 nvidia_benchmark_suite.py` |
| Entity testbed | `python3 orchestrator_testbed.py` |
| Fleet table | `./start.sh fleet` |
| Data stores and lists | `./start.sh data`, `./start.sh data show failed` (launcher 6, option 4) |
| Benchmark report | `./start.sh report` |
| Magpie TTS | `echo "hello" \| ./start.sh tts --voice Magpie-Multilingual.EN-US.Jason` |
| Key status (masked) | `./start.sh status key` |
| Judge | `./start.sh judge rank`, `judge entity`, `judge show`, `judge apply` |
| OpenAI-compatible test server | `./start.sh serve` (launcher 3, testbed 8) |
| `nimlab` command for any folder | `./start.sh shortcut` (launcher 9 Tools) |
| Tests | `python3 -m unittest discover -s tests -t .` |

**Choosing the model list.** Every model menu in the playground (browse, search, test, inspect, compare, code snippet) and the testbed's role hot-swap first asks `1. Verified 200 OK (38)  2. All discovered (243)`. Enter takes the verified list (or the full list when nothing is verified yet). You can still test or assign a model from the full list that has not passed the 200 test; it shows a short note first.

`./start.sh <anything>` passes straight through to `python3 -m nimlab <anything>`.

Testbed chat commands: `/image <path> [prompt]`, `/ocr <path>`, `/deep`, `/code`, `/remember`, `/recall`, `/forget <id>`, `/tools`, `/clear`, `/exit`.

## The judge

### Per-type model ranking

`./start.sh judge rank` (or launcher 5 Benchmark & judge, option 4) runs a fixed battery for each type and builds a leaderboard. Candidates come from `data/models_verified.json`, classified by id and sweep kind; the model currently in the role is always included.

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
- Tool access is controlled in the MCP server's admin console (the per-endpoint toggles): every tool the endpoint lists is offered. See "Tool access".
- `allowed_tools` (`[]`): optional local override. Empty or `["*"]` means every tool the server exposes; a list of names means only those.
- `blocked_tools` (`[]`): optional local override: tool names never offered here.
- `confirm_tool_calls` (false): ask y/N in the terminal before each call
- `max_tool_steps` (4), `max_calls_per_step` (3)
- `tool_timeout_sec` (20), `max_result_chars` (8000), `max_response_bytes` (1,000,000)

**memory_settings**: `recall_top_k` (6), `similarity_threshold`, `rerank_candidates` (16), `recent_on_recall_ask` (3), `hybrid_recall`, `hybrid_keyword_weight`, `exclude_context_turns`, `recall_max_chars`, `search_threshold` (0.3), `trace` (true), and `long_term` (backend, Oracle connection, `owner_user`, `memory_search_tool`, `protected_profiles`, `oracle.text_index`; see "Long-term memory: automatic recall").

**mcp_settings** (v3.7.1 additions): `dedicated_endpoint` (auto), `own_memory_tool`; see "Tool access". `confirm_risky_tools` was removed in v3.7.3 (old configs still load; it is dropped).

**agent_settings**: `name` (the entity's name; default: a custom memory profile, else soul.md).

**routing_settings** (v3.7.1 additions): `environment_block` (true), `migrate_prompts` (true).

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

## NVCF gRPC models (v3.5)

Some models on build.nvidia.com only answer over gRPC at `grpc.nvcf.nvidia.com:443`. The lab calls them with `nvidia-riva-client` (install: `./start.sh install`, or launcher 9 Tools, option 1). Each needs its NVCF function ID, stored in `data/endpoints.json`:

| Command | What it does |
|---|---|
| `./start.sh grpc list` | every gRPC model, its function ID, language, last call |
| `./start.sh grpc refresh [model] [--force]` | fetch IDs from the model's NGC spec (for a stale or missing ID) |
| `./start.sh grpc set <model> <id>` | paste an ID from the "Try API" sample (`--metadata function-id "..."`) |
| `./start.sh grpc lang <model> es-US` | ASR/TTS language (Canary is multilingual) |
| `./start.sh grpc mode <model> offline\|streaming` | ASR mode |
| `./start.sh grpc check [model]` | prove the ID and key work (config RPC) |
| `./start.sh grpc asr <model> clip.m4a` / `grpc tts <model> "text" [--clip me.wav]` | try one |

Set a gRPC model as the ASR or TTS role and it is used over gRPC automatically, behind `testbed` and on the call page. Testbed 6 and launcher 4 Discover & sweep, option 9, have the same tools.

## OpenAI-compatible test server (`serve`)

**v3.7.2: one endpoint, one model name.** `/v1/models` lists exactly one name (`model_name`, default `testbed`), and every route (chat, embeddings, rerank, speech, transcriptions, images) takes that name and hands the request to the right role inside: `POST /v1/embeddings` with `"model": "testbed"` goes to the Embedding role. Clients never need per-role names. A role that is not set answers 400 `role_not_set`: "the Embedding Model role isn't set. Set it with `nimlab setup roles`". The old `expose` switches (per-role and verified debug names) are gone from setup, the settings menu and the defaults: benchmark a role with the benchmark tools and check routing with the route trace in the terminal. An old `server_settings.json` that only held the default `expose` block is cleaned up on load; a hand-set `expose.roles` / `expose.verified` is still read (legacy, manual config only) and lists those names beside the one model, never instead of it.

**v3.4.0: one entity.** UIs see a single model, `testbed`, at `POST /v1/chat/completions`. The persona (soul.md + persona prompt) writes every reply; every other role is an ability it uses behind the scenes. Send text, images, audio, video and files as normal chat content, or ask it to draw, compose or speak. Voice call page: `/call?t=<token>` (link from `./start.sh serve info`). Terminal voice call: testbed 2 or `/call` in chat. See CHANGES.md for the details.

Turns the testbed into an endpoint that any OpenAI-compatible UI or SDK can use (Open WebUI, SillyTavern, LibreChat, Chatbox, the `openai` package, curl). It generates a base URL, its own API key and the model names, and sends each request to the roles you set up. Stdlib only (`ThreadingHTTPServer`), no installs.

**Start it**

| Where | How |
|---|---|
| Launcher | `./start.sh`, then **3 Test server**: start (this phone only, with LAN access, with a tunnel), connection details, UI configs, self-test, request log, server settings, new key |
| Command line | `./start.sh serve` (Ctrl-C stops it), `serve --lan`, `serve --port 9000`, `serve --tunnel`; add `--save` to keep `--port`/`--lan` |
| Inside the testbed | `python3 orchestrator_testbed.py`, **8 Test server**. The server runs in the background while you keep using the testbed and stops when you exit. Requests are not printed there; use the request log (option 5) |

It prints a copy-ready block:

```
Base URL (this phone):   http://127.0.0.1:8765/v1
Base URL (same Wi-Fi):   http://192.168.1.23:8765/v1     (only with LAN access on)
API key:                 sk-testbed-...
Model names:
  testbed-agent        chat
  testbed-persona      chat
  testbed-vision       chat
  testbed-embedding    embedding
  testbed-tts          audio.speech
```

Paste the base URL, key and a model name into the UI. `./start.sh serve info` prints the block again, `./start.sh serve ui` prints ready-made config for Open WebUI, SillyTavern, Chatbox and LibreChat (`librechat.yaml`), a one-line JSON you can turn into a QR code, a curl line and a Python snippet. With Termux:API installed, the menu can copy the block to the clipboard.

**Model names**

- `testbed-agent`: the full orchestrator for each request: intent router, role routing, memory recall with the reranker, the guardrail, MCP tools. Earlier turns in the request become the chat history; an image, audio or video part goes to the matching role. A guardrail block comes back with `finish_reason: "content_filter"`.
- `testbed-<role>`: one per role that is set (`testbed-persona`, `testbed-reasoning`, `testbed-coding`, `testbed-intent-router`, `testbed-vision`, `testbed-ocr`, `testbed-chart-parser`, `testbed-video`, `testbed-omni-audio`, `testbed-guard-translate`, `testbed-asr`, `testbed-tts`, `testbed-image-gen`, `testbed-audio-gen`, `testbed-embedding`, `testbed-reranker`). Each calls that role's backend, whether a model endpoint or an MCP tool. A UI's system prompt is added after the role's own prompt.
- Verified models (off by default): the chat, embedding and rerank models in `models_verified.json`, passed straight to their working endpoint under their own ids.

Every response carries a `testbed` field saying what answered (role, backend, route chosen by the agent, tools used).

**Routes** (Bearer key on everything except `OPTIONS` and `/health`; `x-api-key` also works)

| Route | Goes to |
|---|---|
| `GET /v1/models`, `GET /v1/models/<id>` | the one model name (`model_name`, default `testbed`) |
| `POST /v1/chat/completions` | chat roles and the agent; `stream: true` sends SSE chunks ending in `data: [DONE]` (`stream_options.include_usage` adds a usage chunk). Image parts (`image_url`, URL or data URL) for vision, OCR and charts; `input_audio` for ASR and omni audio; `video_url` for video. Local file paths are refused |
| `POST /v1/embeddings` | Embedding role, called with the one model name (string or list; `encoding_format: base64` works; `input_type` passes through) |
| `POST /v1/rerank` | Reranker role (`query`, `documents`, `top_n`; Cohere/Jina-style results) |
| `POST /v1/audio/speech` | Neural TTS role, **cloned voice included** when one is attached. OpenAI voice names (alloy, nova ...) use the role's own voice; any other name is passed as the voice. `wav` and `pcm` always; `mp3`, `opus`, `aac`, `flac` need ffmpeg (otherwise WAV comes back with an `X-Testbed-Note` header) |
| `POST /v1/audio/transcriptions` | ASR role (multipart `file`, `model`, optional `language`, `response_format` json / text / verbose_json) |
| `POST /v1/images/generations` | Text-to-Image role (`b64_json`, or `url` served from the phone at `/files/...`) |

Errors are OpenAI-shaped (`{"error": {"message", "type", "param", "code"}}`): 401 for a missing or wrong key, 404 `model_not_found`, 400 for a bad request or a model on the wrong route (the message names the right route), 502 `upstream_error` when the role's backend fails. During a stream, a failure arrives as a `data: {"error": ...}` event before `[DONE]`. CORS headers are on every response and preflight `OPTIONS` answers without a key, so browser UIs work.

**Settings** (`data/server_settings.json`, created on first use; change them in the menu or with `./start.sh serve settings <name> <value>`):

| Setting | Default | |
|---|---|---|
| `port` | 8765 | `serve settings port 9000` |
| `lan` / `bind` | off / 127.0.0.1 | `serve settings lan on` binds 0.0.0.0 so other devices on the same Wi-Fi can connect |
| `api_key` | random `sk-testbed-...` | `./start.sh serve regen-key` makes a new one; the old key stops working at once. Never the NVIDIA key |
| `model_name` | `testbed` | `serve settings model quill`: the one name the endpoint serves |
| `model_prefix` | `testbed-` | |
| `log_requests` / `log_to_console` | on / on | request log file / the line printed per request |
| `cors_origin` | `*` | set your UI's origin to lock it down |
| `agent_tool_calls` | deny | when `confirm_tool_calls` is on, nobody can answer that prompt for a remote UI: `deny` refuses those calls, `allow` runs them. The local tool overrides apply either way |
| `stream_chunk_words` | 3 | words per streamed chunk |
| `max_body_mb` | 25 | upload limit |

**Request log:** `./start.sh serve log` (or menu option) shows time, status, route, model and latency per call and a summary. The generated key and the NVIDIA key never appear in full, in the file or on screen.

**Self-test:** `./start.sh serve test` (or the menu) calls the server the way a UI would: model list, a wrong key (must get 401), a CORS preflight, a chat, a streamed chat and embeddings, then prints PASS / FAIL / SKIP with latency. If no server is running, it starts a temporary one for the test.

**Public URL (optional):** with `cloudflared` installed (`pkg install cloudflared`), `./start.sh serve --tunnel` or the menu starts a quick tunnel and shows an `https://...trycloudflare.com/v1` base URL. Anyone with that URL and the key can spend your NVIDIA quota and run your MCP tools, so the key is always required; stop the tunnel when you are done and regenerate the key if it leaks. Any other tunnel works too, pointed at `http://127.0.0.1:<port>`.

**Limits:** one backend call at a time (the agent's memory and history are shared), so parallel requests queue. Streaming is simulated: the role answers in full, then the reply is sent in chunks, with keep-alive comments while it works. Tool/function calling from the UI (`tools` in the request) is not passed on; the agent uses the testbed's own MCP tools.

## Routing: when the reasoning model runs (v3.7)

Normal conversation, small talk, quick questions and "is this working?" checks go straight to the persona. Short everyday turns (up to 16 words, no ask for work) skip the intent router call too. The reasoning role runs only when a turn needs long-context or multi-step reasoning:

- the message plus attached document text is at least `reasoning_min_chars` (4000) characters, or
- it asks for it: analyze, plan, roadmap, trade-offs, step by step, think it through / think deeply, prove, root cause, design a system, summarize this document, and similar.

If the router (or the keyword rules) picks reasoning for anything else, the gate sends it to the persona instead. Coding, vision, image, audio and translation routes are unchanged. Every route and its reason go in the trace (`testbed.route_reason`, the request log, and a `route:` line under each turn in the terminal call; `NIMLAB_SHOW_ROUTE=0` hides that line). The intent router call has its own short timeout.

Settings in `routing_settings` (testbed settings, or `serve settings routing_settings.<key> <value>`): `reasoning_gate` (on), `reasoning_min_chars` (4000), `reasoning_keywords` (on), `chat_fast_path` (on), `chat_max_words` (16), `router_timeout_sec` (8). Turning `reasoning_gate` off brings back the old behaviour.

**When a step fails.** If an ability fails or times out, the persona still answers your message and says exactly what failed and why, for example "the reasoning model timed out after 61s". It keeps that apart from the steps that worked, so a voice turn where ASR and TTS worked doesn't get reported as the voice failing. The terminal call's latency line names each step, for example `Reasoning FAILED 61.0s`, where it used to say "other abilities".

**Fix offers.** For an admin, the report comes with a fix the testbed can make itself, chosen from the error and the verified catalog:

- a timeout: lower `http_settings.timeout_sec` (for example 60 to 20 s), or switch the role to another verified model;
- a missing gRPC function ID, or a 400 from a gRPC-only model: `grpc refresh`;
- a 404 or 5xx: switch to a verified model;
- an unreachable Oracle memory store: switch memory to the local store for now, or run the memory test;
- MCP down: run the MCP test.

Problems it can't fix itself get a hint instead: missing ffmpeg (`pkg install ffmpeg`), or a key to check, since keys are never changed through chat. A fix is applied only after you say yes in a later message, through `self_apply_fix`, with the usual snapshot (so "undo the last change" works) and audit-log entry. Non-admins get the report only. Turn offers off with `nimlab selfadmin fixes off`.

## Public tunnel (Cloudflare)

The server can be reached from outside your network through `cloudflared`. The endpoint key is always required, so a public URL on its own lets nobody in.

- **Quick tunnel:** `nimlab serve tunnel quick` (no account; a random `https://….trycloudflare.com` URL that changes each start).
- **Named tunnel, token:** `nimlab serve tunnel named --token --hostname lab.example.com`, then paste the tunnel token from the Cloudflare dashboard. It is read hidden (or from stdin), saved to `~/.config/nimlab/cloudflared_token` with 600 permissions, passed to cloudflared in its environment (never on the command line), scrubbed from cloudflared's output, and only shown masked. `serve tunnel token-delete` removes it.
- **Named tunnel, credentials file:** `nimlab serve tunnel named <tunnel-id> --credentials ~/.cloudflared/<id>.json --hostname lab.example.com`. The cloudflared config (ingress to the server, 404 for anything else) is written for you to `~/.config/nimlab/cloudflared.yml`.
- `serve tunnel auto on|off` starts the tunnel with every `serve start`; `serve start --tunnel` starts it once. `serve tunnel off`, `serve tunnel status`.
- `serve tunnel install` installs cloudflared when it is missing: `pkg install cloudflared` on Termux, else the official release binary into `~/.local/bin`.
- If cloudflared quits, the server keeps running: you get a warning and it retries after 10 s, 30 s, 60 s, 120 s, … (five tries), then the status says it gave up.

## Updating (update.sh, v3.8.2; git, v3.8.3)

From 3.8.2 on, an update keeps everything you set up. From a git clone (the folder can have any name; `nimlab` is what a plain clone makes):

```bash
cd ~/nimlab                 # your clone, wherever it is
git pull && bash update.sh
```

From a release zip instead: unzip it over the folder (`unzip -o nimlab_3.8.3.zip`, then copy the files from the `nvidia_nim_test_lab` folder it makes over your clone if your folder has another name), then `bash update.sh` inside it. Nothing in Nim Lab depends on the folder's name.

`update.sh` turns off auto-restart first (termux-services/runit, systemd or the built-in supervisor), so nothing comes back while it works; stops only this user's Nim Lab processes (supervisor, server, Telegram poller, scheduler, the tunnel it started), never other Termux work; waits for each to exit before it forces anything; then starts the service once and runs the health check. It prints **GOOD TO GO** only when every check passes, and otherwise the failing check and its fix. Two copies never run at once.

- `bash update.sh --stop`: only stop and clean up (optional, before unzipping).
- `bash update.sh --no-start`: clean up but do not start.
- Keys, settings and memory (`~/.config/nimlab`, `data/`) are never touched. **Service & update > Clean restart** runs the same steps without a new zip.

A fresh install (delete the folder, unzip, `./start.sh`) still works too; it just means running the setup steps again for anything kept in `data/`.

## MCP tools on every channel (v3.8.3)

Before 3.8.3 only terminal chat (and doctor) fetched the MCP server's tool list. Scheduler jobs, the heartbeat, the OpenAI server (so Telegram, Telegram voice notes, inline answers and the voice-call page) and a voice call opened straight from the menu offered Quill no MCP tools at all, which is why a scheduled "pick a tool and play with it" job got "I can't access the tools".

Now the tool list loads the first time any channel needs it (`Entity.ensure_tools()`): thread-safe, fetched once and reused for `mcp_settings.tools_ttl_sec` (default 600 s), fetched again after an MCP error, and after a failed fetch it waits 60 s before trying again so a down server never slows every turn. The reason it failed is kept for `nimlab doctor` and `/health`.

The MCP admin console stays the only authority on which tools exist: whatever the endpoint lists is offered. When a coding role is set, a turn from an ordinary (non-owner) chat leaves tool work to the coding role; scheduled jobs, the heartbeat, prompt-task jobs and owner turns can still use the tools directly.

## Prompt tasks with tools and the Free time job (v3.8.3)

A **prompt task** (`quill_task`) is a job with a prompt and the MCP tools you pick for it. During the run Quill is offered only those tools (plus `memory_search` if it is on) and can call them in its tool loop.

- **Only these tools** (default) or **Any tool** (the picked ones are named as preferred).
- **Must call a tool** (optional): the run is marked failed if Quill called none.
- The run report lists every tool called and how it went (ok, the tool returned an error, the call failed, not run), plus picked tools the server no longer lists. Results go to Telegram, memory or the log as usual.

**From the menu:** main menu **W** (Scheduler), then **8** for the ready-made **Free time** job (hourly; Quill picks one of the tools you choose, plays with it and says what it did; result to Telegram), or **7** for your own prompt task. The tool picker shows the live tool list from the MCP server, 10 to a page: type numbers to tick or untick (`1,3,5-7`), `n`/`p` to page, `/word` to filter, `d` when done. After it is created, `r` runs it once now.

**From the CLI:**

```bash
nimlab jobs tools                                   # the tools the server offers now
nimlab jobs free-time --tools beat_lab,generate_creative_art
nimlab jobs create fun --schedule "FREQ=HOURLY;INTERVAL=1" --do "Play a game" \
    --tools beat_lab,simulate_strategy_games --require-tool      # --any-tool to allow others
```

**From Telegram (owner):** `/jobs tools`, then `/jobs freetime tool_a,tool_b`. `/jobs` shows each prompt task's tools. Quill can create them too when you ask ("make me a free time job with the music tools").

## Model fallbacks (v3.8.3)

When a text role's model can't answer after the HTTP client's own retries (429, any 5xx including an upstream "content safety screening is temporarily unavailable" 503, a timeout or a dropped connection), the same step goes to:

1. the **Reasoning role's model** (persona only), with the persona's prompt and soul and no reasoning text carried over;
2. the role's **secondary list**, in order: roles menu **R**, then **F** (Fallback models), which also sets the cooldown and switches;
3. once a fallback has answered, the primary rests for `routing_settings.fallback_cooldown_sec` (300 s) and the step starts at the fallbacks; then the primary is tried first again.

A 4xx that means the request or the key is wrong does not fall back. Every fallback is logged (`data/fallbacks.jsonl`) and shown in `nimlab doctor` (Model fallbacks) and Telegram `/health`. When every model fails, Telegram says so in plain words, for example "NVIDIA's model was unavailable (HTTP 503: content safety screening is temporarily unavailable). I tried A and B; none of them answered." instead of "server 502: ...".

**Failed steps in bug reports.** A failed step is always in the turn's trace and its bug record: role, model, upstream host and path (never a key or query string), HTTP status, a short upstream body, HTTP attempts, and the fallbacks tried.

**Paced setup sweep.** The 200-OK sweep and the spec rebuild send at most `discovery_settings.probe_rpm` requests a minute (default 30) across all workers, and a 429's Retry-After pauses every worker, so setup doesn't use up NVIDIA's free-tier per-minute limit.

## Custom endpoints (v3.8.2)

Launcher **A** (or `nimlab endpoints ...`) adds any OpenAI-compatible gateway next to NVIDIA. Nothing is set by default.

1. **Add:** a name and the base URL (for example `https://gw.example.com/v1`); the key is typed hidden. `nimlab endpoints add <name> <url>` (`--no-key` for an open endpoint).
2. **Models:** import the gateway's `GET /v1/models` list (`nimlab endpoints import <name>`), or type a model in by hand (`nimlab endpoints model <name> <model> [--kind chat|embedding|rerank|image_gen|tts|asr]`). The kind is guessed from the name and can be changed; models you typed are kept when you import again.
3. **Use on a role:** pick the endpoint's model for a role from the endpoint screen (or set the role's model to `<name>:<model>`).

Routing (one path for every model call: chat, streaming, embeddings, rerank and image generation): a role's explicit endpoint URL wins, then a custom endpoint that serves the model, then NVIDIA's registry. Each endpoint's key is kept in `~/.config/nimlab/secrets.json` (600; the endpoint list itself is `~/.config/nimlab/endpoints.json`, also 600, or `NIMLAB_ENDPOINTS`); `NIMLAB_ENDPOINT_KEY_<NAME>` overrides it for a run. **Your NVIDIA key is never sent to a custom endpoint**, and a host that only looks like yours (`gw.example.com.evil.net`) is not treated as it. A broken endpoints file never breaks NVIDIA calls.

## Health & repair (doctor --fix, /health, v3.8.2)

- `nimlab doctor` runs every check; `--quick` the fast local ones (settings, files, processes and locks, scheduler, Telegram lock, pinned identity facts); `--json` prints a machine-readable report.
- `nimlab doctor --fix` makes **safe repairs only**: it backs up your settings first (to `data/backups/doctor-<time>/`), then fixes file modes (secrets 600, scripts 755), removes pid files whose process is gone, and removes settings that can never work (a role endpoint or `tts_url` that is a website homepage); it never touches a key, a memory or a running process. Then it checks again and shows what is left. Launcher **H** offers the same, and asks first.
- What the doctor now covers: the memory round trip (write, recall by meaning and by keyword, delete) plus an **identity pin round trip** (pins a throwaway fact under its own key, reads it back the way Quill does, removes it; your real facts are untouched), the scheduler (every schedule parses, no broken jobs, and it is running whenever a job is on), and the **Telegram poller lock**: free, held by one live poller, or stale.
- **Stale poller lock:** when a poller dies but a process it started still holds the lock, nobody polls and every start said "another poller is running". Now the next start sees that the owner is gone, stops the leftover (only a recognised Nim Lab process of yours, never a live poller or another program) and takes the lock, so there are no 409 loops and never two pollers.
- **Telegram `/health`** (owner only) runs the quick check read-only and answers with one line per problem; `/health full` runs every check. Repairs are never run from Telegram: it tells you to run `nimlab doctor --fix` in the terminal.

## Keep running (service)

`nimlab service install` keeps the server (plus the tunnel when auto-start is on, and the Telegram bot when `service telegram on`) running and restarts it after a crash. The backend is picked for you, or set with `--backend`:

- **Termux:** a termux-services (runit) service in `$PREFIX/var/service/nimlab` with its own log, installing `termux-services` if needed (close Termux completely once afterwards). `--boot` (or `service boot on`) adds a Termux:Boot script that takes a wake lock and starts it on boot; install the Termux:Boot app, open it once, and turn off battery optimisation for Termux and Termux:Boot.
- **Linux with systemd:** a user unit `~/.config/systemd/user/nimlab.service` (`Restart=on-failure`). **On a VPS you must also turn on linger**, or the service stops when you log out and does not start at boot: `sudo loginctl enable-linger $USER` (install prints this when linger is off; `nimlab platform` and `nimlab doctor` check it). Running as root gets a warning: use a regular user. `sudo nimlab service install --system` writes a system-wide unit `/etc/systemd/system/nimlab.service` that runs as the user who ran sudo (never root) and needs no linger; install one or the other, not both.
- **Anything else:** the lab's own background supervisor.

Only one supervisor runs at a time (v3.7.4): a second copy waits a few seconds for a stopping one, then exits with one log line (under runit it waits a minute first, so runit does not respawn it in a tight loop). The supervisor follows `config_cluster.json`: a part turned on after it started (Telegram set up after the service step, `service telegram on`) starts within seconds without a restart, and a part turned off stops.

Inside, a small supervisor runs each part and restarts a crashed one after 2, 4, 8 … up to 60 seconds; five crashes within two minutes cause a 5-minute pause. The log is `data/service/service.log`, rotated at 1 MB (five kept), with keys and tokens removed. Service files hold no secrets: keys are read at run time from the environment, `~/.nimlab_env` and the private files under `~/.config/nimlab/`.

Commands: `nimlab service install [--boot] | remove | start | stop | restart | status | logs [--lines N] | boot on|off | telegram on|off`. The dashboard shows status, uptime, restart count and the public URL.

## Telegram bot

1. Make a bot with @BotFather and copy its token.
2. `nimlab telegram set-token` reads it hidden, saves it to `~/.config/nimlab/telegram_token` (600), checks it with `getMe` and shows the bot's @username. It is only ever shown masked.
3. `nimlab telegram allow --capture`, then send `/start` to the bot: you become the owner. Or add numeric IDs with `telegram allow <id> …` (`--remove` to take them off). Anyone can send `/id` to learn theirs.
4. `nimlab telegram start` (or `service telegram on` to run it inside the service).

Only people on the allowlist get answers; others get a polite refusal, or nothing with `telegram refusal ignore` (strangers in groups are never answered). Messages go through the same pipeline as `/v1/chat/completions`, as user `telegram:<id>`, with the last ten turns as context (`/reset` clears them). Voice notes go to speech recognition (converted to 16 kHz WAV with ffmpeg) and photos to the vision role; `telegram voice on` adds spoken replies. Replies show "typing…", are split under Telegram's 4096-character limit (code blocks stay closed), use MarkdownV2 with a plain-text fallback, and errors come back as a short message. `telegram mode polling` (default) or `webhook` (through the tunnel, at `/telegram/webhook`, checked with a secret header). `telegram status`, `telegram test`.

One answer per message (v3.7.1): only one poller runs per bot, and every poller and the webhook record each handled `update_id` in `data/telegram/last_update.json` (locked, per bot) and skip anything at or below it, so a stray second poller or an unconfirmed offset never sends a reply twice. The offset is confirmed when a poller or `allow --capture` ends, and capture stops as soon as the owner is saved.

### Telegram commands (v3.8.0, v3.8.1, v3.8.2, v3.8.3)

`/start` and `/help` greet you and list the commands. Owner-only commands (the allowlist's owner): `/status`, `/test`, `/roles`, `/recall <words>`, `/mcp`, `/tunnel`, `/jobs`, `/heartbeat`, `/voice`, `/autoplay`, `/bugs`, `/logs` and `/service`. Anyone allowed can use `/model` (view), `/remember <text>`, `/new` (reset the context), `/cancel` and `/id`.

**The command menu sets itself (v3.8.1).** On every start the bot calls `setMyCommands` twice: the default menu (what anyone allowed can use) and a full menu for the owner's private chat. BotFather `/setcommands` is not needed any more. To leave the menu alone, set `telegram_settings.set_commands` to `false`.

**/model** shows the exposed model name (one name for the whole stack) and the primary (persona role) model. The owner can switch: `/model primary <model id>` sets the persona role (the model has to be on the verified or discovered lists, the same check as `self_set_role`), and `/model name <name>` renames the exposed model (applies when the server restarts). Each switch asks first with Switch / Cancel buttons, takes an undo snapshot (`nimlab selfadmin undo`) and is written to the self-admin audit log. `telegram_settings.model_switch: false` makes `/model` view-only.

**/remember <text>** saves a memory for you (scoped to your Telegram user, like your chat turns). "My name is ..." is also pinned as an identity fact, so Quill knows it on every channel. Same as `nimlab memory add <text>`.

**/voice [on|off]** switches spoken replies to voice notes (the same setting as `nimlab telegram voice on|off`); no argument switches it.

**/service** shows the service status; `/service restart` asks first (Restart / Cancel button) and restarts two seconds after you press it, so the answer reaches you before the bot goes down.

**/cancel** stops the reply in progress in this chat: Quill's answer is dropped when it arrives, and nothing is sent. A new message while a reply is still being worked on also replaces it. Since 3.8.1 replies run off the polling thread, so `/cancel` and commands answer at once while Quill is thinking.

**/health [full]** (v3.8.2, owner only) runs `nimlab doctor --quick` read-only (or every check with `full`) and answers with the overall verdict, the process line and one line per warning or problem with its fix. It never repairs anything; for repairs use `nimlab doctor --fix` in the terminal.

**/heartbeat** shows the heartbeat status with buttons: "Run a heartbeat now" and one button per suggested action to switch it on or off. `/heartbeat run` still works.

**Buttons.** Every button carries a one-time token that only the person who asked can press. Confirmation buttons expire after ten minutes, heartbeat buttons after a day; a restart of the bot expires them all ("That button has expired. Send the command again.").

**Inline mode (v3.8.1).** Type `@Quill_svn_bot` (your bot's name) and a question in any chat: Quill's answer appears as a result you can post. Turn it on once in @BotFather with `/setinline` (Telegram needs this step; the bot can't do it for itself). Only the owner gets answers unless `telegram_settings.inline` is `"allowlist"` (anyone on the allowlist) or `"off"`. If Quill takes longer than `telegram_settings.inline_timeout` seconds (default 8), the result posts your question as it is instead, with a button to open the private chat. Inline answers use no admin tools.

**/autoplay [on|off|status]** plays Quill's voice replies on the phone's own speaker too, right after they are sent to Telegram, so you don't have to tap play. With no argument it switches on or off; the state is kept in `data/tg_autoplay.json`. It uses `termux-media-player` (`pkg install termux-api` plus the Termux:API app), else `play-audio`. It only has something to play when spoken replies are on (`nimlab telegram voice on`), and it says so; off Termux (a VPS) it says the phone speaker isn't available. A missing or failing player is logged and never stops the reply.

The bot registers this list itself (see above). To paste it by hand anyway (@BotFather, `/setcommands`):

```
start - Hello and the command list
status - System & endpoint health
health - Health check (read-only)
test - Run checks (doctor)
model - Exposed model and primary
roles - Show the role model stack
recall - Search memory
remember - Save a memory
mcp - MCP server & tool status
tunnel - Tunnel status & public URL
jobs - Scheduler jobs
heartbeat - Heartbeat status or run one
voice - Spoken replies on or off
autoplay - Play voice replies on the phone speaker
bugs - Recent errors with bug IDs
logs - Tail the service log
service - Service status or restart
new - Reset conversation context
cancel - Stop the reply in progress
help - List the commands
```

## Phone audio bridge (nimbridge, v3.8.5, v3.8.6)

Nim Lab on a VPS has no speaker or mic. A phone running the nimbridge Termux client plays Nim Lab's audio (Telegram /autoplay, the terminal voice call, clips an agent publishes) and can lend its mic to the voice call.

To add a phone: launcher **F Phone audio bridge** (or **P** on the Test server screen), `nimlab audio setup`, or the optional last step of `nimlab setup`. Give the phone a name, choose whether calls may use its mic and confirm the server address. Nim Lab prints the phone's key once and then one block between `# ===== BEGIN NIMBRIDGE SETUP` and `# ===== END NIMBRIDGE SETUP` lines. Install Termux and the Termux:API app on the phone, then paste the whole block into Termux. It installs curl, jq and termux-api, writes the nimbridge script and the phone's settings, checks the key with the server, asks for the mic once if you turned it on, and starts the bridge. The block holds that phone's key, so paste it only on that phone.

For scripts: `nimlab audio add NAME --termux [--mic on|off] [--url URL]` prints only the block. `nimlab audio add NAME` prints only the key, for `nimbridge setup` on the phone. The client's source is `nimlab/clients/nimbridge.sh`. On the phone: `nimbridge status | stop | start | use | mic on|off | talk | logs | boot`.

## Self-admin

The testbed entity can read and change its own setup through tools, but only for admins: you at the terminal, requests that use the admin key (`nimlab selfadmin admin-key` makes one, saved with 600 permissions and shown once), and the Telegram owner. Everyone else gets no admin tools, and a call to one is refused and logged.

- **Read:** status, config, roles, prompts, logs, the model catalog (`self_status`, `self_get_config`, `self_get_roles`, `self_get_prompts`, `self_logs`, `self_catalog`). Keys and passwords are always masked.
- **Change:** roles (checked against the catalog, with suggestions), settings, prompts, memory options, server settings, jobs (gRPC refresh/check, memory test, MCP test, server self-test, discover, sweep), the service and the tunnel.
- **Undo:** the config is saved before every change; "undo the last change" or `nimlab selfadmin undo` rolls it back (the last 30 are kept).
- **Confirmation:** restarting or stopping the service, turning the tunnel off, and changing security-related settings (enabled flags, auth, guard, LAN, CORS, …) need your yes in a separate, later message (a one-time code, valid ten minutes, only for the person who asked).
- **Never through chat:** secrets, and the self-admin settings themselves.
- **Audit log:** every change, refusal and confirmation goes to `data/selfadmin/audit.jsonl` (secrets masked); `nimlab selfadmin audit [n]`.
- **Shell and file edits** (`self_shell`, `self_edit_file`) are a separate switch, off by default (`selfadmin shell on`), limited to the project folder and always confirmed.

`nimlab selfadmin status | on | off | shell on|off | others-read on|off | fixes on|off | admin-key | undo | audit`.

## MCP flow

The testbed talks to the MCP server over Streamable HTTP: `initialize`, then `notifications/initialized`, then `tools/list` (with paging), then `tools/call`. It accepts JSON or SSE responses and carries `Mcp-Session-Id` and `MCP-Protocol-Version` forward. A model's tool call must be strict JSON:

```
<tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>
```

The older `<tool_call name="...">{...}</tool_call>` form is still accepted. Since v3.7.1 the parser also takes what models really send: several JSON objects in one block (one per line, or a JSON array; MiniMax does this for parallel calls), `"parameters"` in place of `"arguments"`, the OpenAI `{"type": "function", "function": {"name", "arguments": "<json string>"}}` shape, a ```json fence inside the block, MiniMax's `<minimax:tool_call><invoke name=...><parameter name=...>` form, and the native `tool_calls` field of a chat completion. Each object is still parsed strictly. Each call is checked in order: it must parse, the tool must have been advertised by the server, the arguments must match its `inputSchema`, it must not be left out by a local override (`allowed_tools` / `blocked_tools`), and, only when `confirm_tool_calls` is on, you must confirm it. Anything that fails is reported back to the model as a rejected call and nothing runs. Results come back to the model fenced as untrusted data, truncated to the size limit, with any tags inside them neutralized.

## Tool access (v3.7.3)

**Tool access is controlled in the MCP server's admin console.** You switch on there which tools each endpoint may use, and the lab trusts that: every tool the endpoint lists is offered to the persona and the roles. There is no risky-tool filter, no blocking on tool annotations and no default block on other agents' `*_mem` tools; to keep a tool away from Quill, switch it off for Quill's endpoint in the admin console. Tool calls run without asking unless you turn on `confirm_tool_calls`.

At startup the terminal shows one line, for example `[MCP] 214 tools from https://svn-dev.online/mcp-quill, all available`. When a local override leaves tools out it says so: `[MCP] 214 tools from ...: 212 available, 2 left out by local overrides (blocked_tools: terminal, send_gmail_message)`. `nimlab mcp tools` (or `nimlab mcp test -v`, or `/tools` in chat) lists every tool, one per line.

- `mcp_settings.allowed_tools` (default `[]`): optional local override. Empty or `["*"]` means every tool the server exposes; a list of names means only those.
- `mcp_settings.blocked_tools` (default `[]`): optional local override: tool names never offered here, whatever `allowed_tools` says.
- `mcp_settings.confirm_tool_calls` (default `false`): ask y/N before every tool call (reading the entity's own memory never asks).
- **Dedicated agent endpoint.** Point the MCP URL at your agent's own endpoint, for example `https://svn-dev.online/mcp-quill` or `https://svn-dev.online/mcp/quill`. The tools are the ones switched on for that endpoint in the admin console. Detection recognises `/mcp/<agent>`, `/mcp-<agent>`, `/<agent>/mcp` and `/<agent>-mcp`; `dedicated_endpoint`: `auto` (default), `true` or `false`. It only changes what the summary says. Switch to one in Settings > MCP > 8 or in `nimlab setup mcp`.
- Upgrading from 3.7.1 or 3.7.2: `confirm_risky_tools` is dropped and `confirm_tool_calls` is set to the new default (off) the first time the config loads; an empty `allowed_tools`, which used to mean no tools, now means all.
- `own_memory_tool`: the one MCP memory tool that is this entity's own (for example `quill_mem`). It is always allowed, even if a local override would leave it out, and reading from it (recall, recent, get) never asks. Name it after the memory profile (profile `QUILL`, tool `quill_mem`) so both point at one profile. The MCP test and `nimlab doctor` check that its schema has an `action` with `recall` and a `query`, like `charlie_mem`. Long-term memory never depends on it (see below).
- When the model writes tool-call markup anyway, or chat-template tokens leak (`]<]minimax[>[`, `<|im_end|>`, `<|python_tag|>`, gpt-oss `<|channel|>`, Hermes/Qwen `<tool_call>`, Mistral `[TOOL_CALLS]`, DeepSeek tokens), they are removed from the reply and from the streamed tokens before you see them. When the tool loop reaches `max_tool_steps`, the persona is asked once more with no tools and writes a real answer from what the tools returned; the leftover call is never shown.

## Long-term memory: automatic recall (v3.7.1)

Memory works through the store you configured (the direct Oracle connection with your wallet or TLS string, the local file, or JSON), never through an MCP tool and never by the model deciding to call one. Every turn, in the terminal chat, voice calls, the served endpoint and Telegram, goes through the same pipeline as `/v1/chat/completions`:

1. **Before the persona runs: semantic recall.** The message is embedded with the embedding role and the closest memories are found with `VECTOR_DISTANCE` on the entity's own table (`MEM.TESTBED_MEMORIES`, or your custom profile's table), reranked by the reranker role when it is set, and put in the persona's context as RECALLED SEMANTIC MEMORY. A question like "what were we just talking about on the voice call?" names no topic a vector can match, so the newest memories in your scope are added as MOST RECENT MEMORIES (`memory_settings.recent_on_recall_ask`, default 3, 0 = off).
2. **After the reply: store.** The turn is saved (subject to `store_mode` and de-duplication).
3. **Trace.** Each step logs one line, for example `[memory] recall oracle MEM.TESTBED_MEMORIES: 3 hit(s) + 2 recent, reranked in 412 ms` and `[memory] store oracle: 1 memory(s) saved in 230 ms`; an unreachable store says `offline` with the reason. `memory_settings.trace: false` hides them. The terminal shows the store, its count and the modes at startup.

**Scope.** With `scope: "user"`, the terminal chat, voice calls and requests with no `user` field use `long_term.owner_user` as their key, so they recall the same memories; Telegram users and API callers with a `user` field get their own.

**Keyword search, on request.** Semantic recall finds meaning; it can miss an exact name, bug ID, number or phrase. For that the persona has a built-in `memory_search` tool that runs in-process against the same connection (not MCP):

- `mode: "semantic"`: vector search only; `mode: "keyword"`: exact words (quote a phrase: `"voice call"`); `mode: "both"` (default): both, merged, de-duplicated by record, then reranked when the reranker role is set.
- Keyword search uses an **Oracle Text index** (`CONTAINS`, created by `memory setup` as `MEM.<PREFIX>_MEM_TEXT_IX`, kept in sync on commit; `oracle.text_index: false` skips it). Without Oracle Text it falls back to `DBMS_LOB.INSTR` on the lowered text. The local store uses an SQLite FTS5 index (LIKE when FTS5 is missing); JSON scans.
- `long_term.memory_search_tool`: `auto` (default) offers it whenever the persona has a tool loop anyway; `on` always offers it (the persona then answers without token streaming); `off` never. `memory_settings.search_threshold` (0.3) is the similarity floor for its semantic half.

**Memory profile name.** The default profile is `TESTBED` (tables `MEM.TESTBED_MEMORIES` / `TESTBED_META`). `nimlab setup memory` offers an optional custom name; other agents' names on the shared MEM schema (CHARLIE, MAYA, MILES, SIMONE and others, plus Oracle's own) are refused, and `long_term.protected_profiles` adds more. `agent_settings.name` sets the entity's name used for the dedicated endpoint and the environment block (default: a custom profile name, else soul.md's `# SOUL.md — Entity: "Name"` header).

## Scheduler and heartbeat (v3.8.0)

The scheduler runs jobs like Oracle's DBMS_SCHEDULER: calendar strings (`FREQ=MINUTELY;INTERVAL=30`), cron lines or one-off `at` times; retries that back off, a time limit, overlap limits, catch-up after downtime (one, none or all), a job that fails too often in a row is switched off as broken, plus run history and an audit log. Only one scheduler runs at a time; the service runs it beside the server and the bot (`nimlab service scheduler on|off`). `nimlab jobs`, `nimlab scheduler status`, main menu Scheduler, and `/jobs` on Telegram.

**The heartbeat** is a built-in job, off until you turn it on, every 30 minutes. Each run Quill looks at fresh context and decides which of its suggested actions are worth doing (health-check, bug-review, tunnel-recover, memory-digest), within `heartbeat_settings` limits on actions, tokens and time, and writes a report. Results go to Telegram, memory, the log, an MCP tool or nowhere: always, only on failure, or only when notable; failures also go to Telegram.

To turn it on:

1. `nimlab heartbeat enable` (or `/heartbeat` on Telegram to check it).
2. The service runs the scheduler by default (`nimlab service scheduler on` if you switched it off). If the service is already running, `sv restart nimlab` (or `nimlab service restart`) so it picks the change up.
3. Try one now: `nimlab heartbeat run-now` (or `/heartbeat run` on Telegram), then `nimlab heartbeat reports`.

Change how often with `nimlab heartbeat schedule "FREQ=MINUTELY;INTERVAL=60"`; edit the actions with `nimlab heartbeat actions`; `nimlab heartbeat disable` turns it off.

## Memory recall fix (v3.8.0)

In 3.7.x, "My name is SeVin" said on Telegram was saved, but a terminal call asking "what did I tell you my name is" could not find it: it ranked about third, behind an old "I do not remember who you are" answer and a turn already in the conversation, and only three memories were recalled. Now:

- **Pinned identity facts.** Self-introductions ("my name is ...", "call me ...", "I'm SeVin", "I live in ...", "my birthday is ...", "my pronouns are ...") are stored as `identity` records in your scope and put in front of Quill on every turn and channel as KNOWN FACTS ABOUT THE USER. A new name replaces the old one. Introductions saved before 3.8.0 are found and pinned once, the first time. `long_term.pin_identity: false` turns this off.
- **Hybrid recall.** Each turn runs vector similarity and keyword search side by side (Oracle Text `CONTAINS` on Oracle, `INSTR` without Oracle Text, FTS5 on the local store, a word scan on JSON and the offline queue), ranks them together (reciprocal rank fusion), then the reranker when it is set. Plain SQL, no stored procedures. `hybrid_recall: false` goes back to vector only.
- **No duplicates of what's already in context.** Turns already in the conversation's short-term history are left out of recall (`exclude_context_turns`).
- **Identity questions count as memory questions.** "What's my name", "who am I", "what did I tell you", "do you remember me" also add the newest memories, like "remember" questions did.
- **What is never stored or recalled.** The setup self-test's requests (they carry `X-Nimlab-Self-Test: 1`, and its fixed prompts are recognized too) and Quill's own "I don't remember / I don't know who you are" answers. Ones older versions stored are skipped at recall.
- **More room.** `recall_top_k` 6 (was 3), `rerank_candidates` 16, within `recall_max_chars` (2400).
- **Two processes, one store.** The JSON and local stores pick up memories another process (the Telegram bot in the service) wrote since they loaded. JSON merges on every write under a file lock (`data/memory.json.lock`): nothing another process wrote is overwritten, and a record deleted elsewhere stays deleted.

The recall trace now reads like `[memory] recall oracle MEM.TESTBED_MEMORIES: 6/6 hit(s) scores [...] (vector 12, keyword 5, 1 already in context) in 240 ms`.

## System prompts and the ENVIRONMENT block (v3.7.1)

The persona, reasoning and coding prompts get an **ENVIRONMENT** section built from the live settings on every turn, so they never go stale when tools or settings change. It says the entity's name and memory profile; the memory store and whether it is connected; that recall happens automatically before every reply and saving after it (so the model never calls a tool to log or recall); the `memory_search` tool when it is offered; the exact MCP tool names the model may call and that no other tools exist; the abilities the testbed runs for it; and the channel (terminal, voice call, Telegram, endpoint) with its output rules. On voice channels the rules are spoken sentences only, no lists or markdown, and they win over soul.md's preference for lists and artifacts. `routing_settings.environment_block: false` turns it off.

**Prompt lint.** At startup and in `nimlab doctor`, every system prompt (and soul.md) is checked for tools it tells the model to call that are not available, for example `[prompts] warning: persona mentions quill_mem, which is not an available tool`.

**Migration.** The first start of v3.7.1 rewrites, once, the sentences in your `config_system_prompts.json` that tell a model to call a tool that does not exist (`log ... via quill_mem(action='log')`, `ready for quill_mem(...)`, `Plan and chain required MCP tool calls`), keeps every other word, adds to the persona that memory recall and saving are automatic, and saves a backup next to it (`config_system_prompts.json.bak-<date>`). Roles that had nothing stale are left exactly as they were. `routing_settings.migrate_prompts: false` skips it. The shipped default prompts no longer name tools.

## Doctor (v3.7.1)

`nimlab doctor` checks the parts that fail quietly:

- **Long-term memory**: connects with your wallet or TLS string, writes a marked test memory, finds it by semantic recall (`VECTOR_DISTANCE`) and by keyword search (Oracle Text or INSTR, which it names), deletes it, and shows the time of each step.
- **Settings** (v3.7.2): a `voice_settings.tts_url` / `asr_url` that is a website homepage instead of a speech endpoint, role models or fallbacks that are bare URLs, and role endpoints that are homepages, each with the fix.
- **System prompts**: the lint above.
- **MCP tools**: how many the server exposes and how many the persona may use, and whether `own_memory_tool` is listed with a fitting schema. `--no-mcp` skips it.

## Self-test (v3.7.1, v3.7.2)

v3.7.2: everything is tested through the one model name, so a default install never SKIPs a check because roles aren't listed: embeddings, rerank and speech (TTS) are each sent with the agent's model name. A capability whose role is not set is a SKIP that says so ("the Embedding Model role isn't set: run `nimlab setup roles`"). Setup and the self-test still end in the main menu, pass or fail.


`nimlab serve test` runs the basic checks (models list, auth, CORS, chat, streaming, the identity from soul.md) and then the heavy live checks (a picture and an audio tone in one message, image generation). Setup runs only the basic ones (`serve test quick`); `setup_full_self_test: true` runs both. A check that times out or loses the connection is that check's FAIL with the reason (`timed out after 240 s waiting for a reply`) and a bug ID, and the test goes on; it no longer ends setup with a traceback or suggests the port is busy. The summary says which checks failed and whether the server itself is fine. Timeouts: `server_settings.self_test_timeout_sec` (basic, 90) and `self_test_heavy_timeout_sec` (heavy, 240).

## Text-to-speech input (v3.7.1)

Text sent to the TTS role is cleaned first: tool markup, template tokens, code blocks, links, markdown, brackets and control characters are removed (Riva/Magpie on Triton reject some of them with HTTP 400 "multichar start character"). When the TTS model still answers 400 about a character, it is retried once with a stricter clean. When TTS fails, the reply stays as text and the terminal says so.

## Bug log (v3.7.1)

`nimlab bugs list|show <id>|tail|status`: errors grouped under short IDs such as `B-3F9A1C`, with where it happened, the upstream error, the routing trace and timings, secrets removed. Settings in `server_settings.json` under `bugs`: `enabled`, `max_mb` (5), `keep_days` (14), `compress`, `max_event_kb` (64), `trace_in_request_log`.

## Router benchmark (v3.7.2)

`nimlab bench router [--runs N] [--call] [--only ids] [--prompt TEXT] [--compare] [--show]` (also Benchmarks > Router in the menu) times the testbed's own turn pipeline, the same code testbed chat and voice calls use: a text turn goes through `Entity.turn`, a turn with a picture or a recording through the attachment pipeline, and `--call` through the voice-call pipeline (voice channel, the call's turn time cap, a spoken reply, memory stored after the reply). So the intent router, the keyword and media fast paths, the persona, the role calls to NVIDIA and memory recall/store all run as they do for you.

The built-in prompts cover each route: casual chat, reasoning, coding, a tool call, a picture (vision), a screenshot (OCR), a chart, a voice message (ASR), a memory question and a spoken reply; `--prompt` adds your own. Per turn it records the route chosen against the expected one (accuracy), the router's decision time (0 when a fast path decided), every HTTP call (bytes sent, time to the first byte, total time, bytes received), memory recall and store time, and the end-to-end time split into router, NVIDIA API, memory and the pipeline's own overhead. With `--runs N` each prompt repeats N times and the report shows the median and p95 per prompt and per route. `--compare` also calls the same models directly (one role call, no router, persona or memory) to show what the full turn adds. The last run is saved to `data/router_bench_latest.json` and a summary goes on the benchmark history (kind `router`); `--show` prints it again. It sends real requests on your key.

<!-- settings-reference:start -->
## Deploy on a Linux VPS (Oracle Cloud Always Free)

Tested shape: OCI Always Free **VM.Standard.E2.1.Micro** (x86_64 AMD, 1/8 OCPU with bursting, 1 GB RAM) with Ubuntu or Oracle Linux. Everything also works on any other small Linux box.

1. **Log in as a regular user** (`ubuntu` on Ubuntu images, `opc` on Oracle Linux). Do not run Nim Lab as root.
2. **Add swap** (1 GB RAM is tight for pip and the 200 OK test; setup and `nimlab doctor` warn when RAM is under 1.5 GB and there is no swap):
   ```bash
   sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
3. **System packages:**
   - Ubuntu / Debian: `sudo apt-get update && sudo apt-get install -y python3-venv python3-pip ffmpeg unzip`
   - Oracle Linux: `sudo dnf install -y python3-pip unzip`. ffmpeg (for Telegram voice notes) is not in the base repos: enable EPEL and RPM Fusion (free), then `sudo dnf install -y ffmpeg`.
4. **Unzip and install:** `unzip nimlab_<version>.zip && cd nvidia_nim_test_lab && ./start.sh install`. On Ubuntu 23.04+ and Debian 12 the system Python refuses pip (`externally-managed-environment`, PEP 668); `start.sh` then makes a venv in `.venv` inside the project (or `~/.local/share/nimlab/venv` when the project folder is read-only) and installs there. It never uses `--break-system-packages`. From then on `./start.sh`, the `nimlab` shortcut and the service all run the venv's Python. pip prefers wheels (`--prefer-binary`), so nothing is built from source when a wheel exists.
5. **cloudflared** (for the public tunnel): `nimlab serve tunnel install` downloads Cloudflare's release binary into `~/.local/bin`. Or use Cloudflare's package repo (https://pkg.cloudflare.com/index.html):
   - Ubuntu / Debian:
     ```bash
     sudo mkdir -p --mode=0755 /usr/share/keyrings
     curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
     echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
     sudo apt-get update && sudo apt-get install cloudflared
     ```
   - Oracle Linux: `curl -fsSl https://pkg.cloudflare.com/cloudflared.repo | sudo tee /etc/yum.repos.d/cloudflared.repo && sudo dnf install cloudflared`
   Without cloudflared the server still works locally; starting a tunnel says so and prints the install command for your system.
6. **Setup:** `./start.sh setup`, as on the phone. Then `nimlab serve tunnel quick` (or a named tunnel) and `nimlab service install`.
7. **Linger:** `sudo loginctl enable-linger $USER`, so the service keeps running after you log out and starts at boot.
8. **Check:** `nimlab platform`, then `nimlab test all`.

**Networking.** Keep the server on `127.0.0.1` (the default) and use the Cloudflare tunnel: cloudflared connects out, so no inbound port is opened. Opening a port on Oracle Cloud takes two changes: an ingress rule in the VCN security list (or network security group), and the instance firewall, because Ubuntu images ship iptables rules that only allow port 22 (Oracle Linux uses firewalld). Both are needed; one alone leaves the port closed.

**What differs from Termux.** The terminal voice call (termux-microphone-record / termux-media-player) is Termux-only: off a phone its menu entry says so and it does not start. Telegram voice notes still work (they need ffmpeg). The battery features (wake lock, Termux:Boot) are skipped; systemd starts the service at boot instead. On a 1 GB box the 200 OK test and discovery use at most 2 parallel probes (1 under 768 MB) and drop each model's page plan once it is probed.

`nimlab platform` (and the Platform section of `nimlab doctor`, and `nimlab test platform`) shows the OS, Python version, venv, ffmpeg, cloudflared, linger and RAM/swap, with the install command for anything missing.

## Tests (v3.7.4)

Main menu **E Tests** (or `nimlab test`) lists one test per part of the lab; pick one to run it, or **a** to run them all and get a pass / fail table. `nimlab test <name>` runs one, `nimlab test all` runs everything (exit code 1 when one fails), `nimlab test history` shows the last runs. Each result is **pass**, **fail** or **skip** with the reason and the time it took. A failure gets a bug ID from the bug log (`nimlab bugs show <id>`) and says what to run next, with the matching `nimlab troubleshoot` entry. A skip says how to turn the part on. Tests marked * send real requests on your NVIDIA key. Every run is saved to `data/test_history.jsonl` (last 300).

The tests reuse the lab's own checks (the memory roundtrip, the server self-test, the gRPC check, the tunnel test, the config lint) instead of separate copies. The list is in the [Command reference](#command-reference).

**Commands & troubleshooting (v3.7.4).** Main menu **H** lists every command by area with a one-line description; pick one to run it (arguments are asked for, commands that stop, delete or change something ask first) and you come back to the list. It also has a troubleshooting guide by symptom (run the steps one by one, or all in order with a question before each) and a tunnel test: `GET <public URL>/v1/models` with the server's own key (never shown), reporting 200 / 401 / 530 or 1033 / DNS in plain words, with an optional one-turn chat through the tunnel. The same list prints with `nimlab commands [area]` (alias `nimlab help`), the guide with `nimlab troubleshoot [symptom]`.

## Command reference

<!-- BEGIN COMMAND REFERENCE (generated by: nimlab commands --markdown) -->
Every command, grouped. The launcher's main menu has the same list under **Commands & troubleshooting** (pick one to run it), and `nimlab commands [area]` prints it. *asks first* = stops, deletes or changes something; *real requests* = sends requests on your NVIDIA key; *interactive* = asks questions or runs until Ctrl+C.

**Setup**

- `nimlab setup`: Run the guided setup from the first step *(interactive)*
- `nimlab setup list`: Show every setup step and where it stands
- `nimlab setup <step>`: Run one setup step (key, discover, functions, sweep, mcp, roles, grpc, memory, server, telegram, selfadmin, deps, shortcut, tunnel, service) *(interactive)*
- `nimlab shortcut install`: Install the `nimlab` shortcut command
- `nimlab shortcut status`: Show whether the shortcut is installed and where
- `nimlab shortcut remove`: Remove the `nimlab` shortcut *(asks first)*
- `nimlab platform`: Show this machine: OS, Python, venv, ffmpeg, cloudflared, RAM and swap, with hints

**Keys**

- `nimlab status <key|live|inventory|memory|catalog|discovered|endpoints|roles|color>`: One status field: key, live, inventory, memory, catalog, discovered, endpoints, roles, color
- `nimlab persist-key`: Save the NVIDIA key so new shells and the service find it *(asks first)*
- `nimlab forget-key`: Remove the saved NVIDIA key *(asks first)*
- `nimlab mcp set-key`: Enter the MCP API key (hidden) and save it outside the project *(interactive)*
- `nimlab mcp key-source`: Show where the MCP key comes from (env, saved or session)
- `nimlab mcp delete-key`: Delete the saved MCP key *(asks first)*
- `nimlab serve regen-key`: Make a new API key for the local server (clients need the new one) *(asks first)*
- `nimlab selfadmin admin-key`: Make or show the self-admin key *(asks first)*

**Models (discover, sweep, gRPC, roles, fleet)**

- `nimlab endpoints`: Custom endpoints and their models
- `nimlab endpoints add <name> <url>`: Add your own OpenAI-compatible gateway (asks for the key)
- `nimlab endpoints import <name>`: Add the models a custom endpoint lists
- `nimlab endpoints model <name> <model> [--kind <kind>]`: Add a model to a custom endpoint by hand
- `nimlab ui endpoints`: The Custom endpoints menu *(interactive)*
- `nimlab discover`: Find the models your key can see (uses the saved catalog when fresh) *(real requests)*
- `nimlab discover --refresh`: Discover again from NVIDIA, ignoring the saved catalog *(real requests)*
- `nimlab sweep`: The 200 OK test: one small request per model, writes the verified fleet *(real requests)*
- `nimlab sweep --plan-only`: Show what the 200 OK test would send, without sending it
- `nimlab roles`: Show which model plays each role
- `nimlab roles show`: Same as roles
- `nimlab roles candidates <role>`: List the models that can play one role
- `nimlab roles migrate`: Rewrite old role settings into the current form *(asks first)*
- `nimlab fleet`: Show the verified fleet from the last 200 OK test
- `nimlab grpc list`: List gRPC-only models and their function IDs
- `nimlab grpc menu`: The gRPC menu *(interactive)*
- `nimlab grpc check`: Check every gRPC function ID with a real call *(real requests)*
- `nimlab grpc asr`: Transcribe a short clip through the ASR function *(real requests)*
- `nimlab grpc tts`: Speak a line through the TTS function *(real requests)*
- `nimlab grpc fill`: Look up missing function IDs from the model pages
- `nimlab grpc refresh`: Read every model page again for function IDs
- `nimlab grpc set <model> <function-id>`: Set one model's function ID by hand *(asks first)*
- `nimlab grpc clear <model>`: Forget one model's function ID *(asks first)*
- `nimlab grpc lang <model> <language>`: Set the language code for a speech model *(asks first)*
- `nimlab grpc mode [<mode>]`: Show or set how gRPC models are called
- `nimlab tts`: Speak a test line with the TTS role *(real requests)*
- `nimlab judge rank`: Rank candidate models for the roles with judge models *(real requests)*
- `nimlab judge entity`: Judge whole persona setups *(real requests)*
- `nimlab judge show`: Show the last judge results
- `nimlab judge apply`: Apply the judge's picks to the roles *(asks first)*

**Server and tunnel**

- `nimlab audio devices`: Phones on the audio bus (nimbridge); * marks the active one
- `nimlab audio setup`: Register a phone step by step and print a ready-to-paste Termux block
- `nimlab audio add <name> [--label <label>]`: Register a phone for nimbridge and print its token once
- `nimlab audio add <name> --termux [--mic on|off] [--url <url>]`: Register a phone and print only its Termux block (for scripts)
- `nimlab audio remove <name>`: Forget a phone (its token stops working)
- `nimlab audio use <name>`: Make this phone the active one: audio and mic requests go to it only
- `nimlab audio release`: No active phone: nothing is relayed
- `nimlab audio tone [--target <name>]`: Play a short test tone on the active phone
- `nimlab audio say [<text>] [--target <name>]`: Speak text with the TTS role on the active phone
- `nimlab serve start`: Start the local OpenAI-style server in this terminal (Ctrl+C stops) *(interactive)*
- `nimlab serve start --tunnel`: Start the server with the public tunnel *(interactive)*
- `nimlab serve info`: Show the server address, model name and how to connect
- `nimlab serve test`: Self-test the running server through its one model name *(real requests)*
- `nimlab serve models`: List what the server's /v1/models returns
- `nimlab serve log`: Show the server's request log
- `nimlab serve ui`: Show the browser chat page address
- `nimlab serve settings`: Show or change server settings
- `nimlab serve menu`: The server menu *(interactive)*
- `nimlab serve`: Same as serve menu *(interactive)*
- `nimlab serve tunnel status`: Show the tunnel mode, whether it runs and its URL
- `nimlab serve tunnel quick`: Use a quick tunnel (random trycloudflare.com URL) *(asks first)*
- `nimlab serve tunnel named`: Use a named Cloudflare tunnel (asks for the token) *(interactive)*
- `nimlab serve tunnel off`: Turn the tunnel off (server stays local) *(asks first)*
- `nimlab serve tunnel auto <on|off>`: Start the tunnel together with the server, or not *(asks first)*
- `nimlab serve tunnel install`: Download cloudflared
- `nimlab serve tunnel token-delete`: Delete the saved tunnel token *(asks first)*
- `nimlab test tunnel`: Test the tunnel: /v1/models through the public URL with the server key

**Background service**

- `nimlab service status`: Is the service running, its children, restarts and stray copies
- `nimlab service brief`: One-line service state
- `nimlab service logs`: The service log (last lines)
- `nimlab service start`: Start the background service
- `nimlab service stop`: Stop the background service (server and bot stop too) *(asks first)*
- `nimlab service restart`: Restart the background service *(asks first)*
- `nimlab service install`: Install the service (runit on Termux, systemd on Linux) *(asks first)*
- `nimlab service remove`: Stop and remove the service files *(asks first)*
- `nimlab service cleanup`: Stop stray supervisor, server and bot copies *(asks first)*
- `nimlab update`: Clean restart after unzipping a release: stop, clean up, start once, health check *(asks first)*
- `nimlab update --stop`: Stop and clean up only (optional, before unzipping) *(asks first)*
- `nimlab ui service`: The Service & update menu *(interactive)*
- `nimlab service telegram <on|off>`: Run the Telegram bot inside the service, or not *(asks first)*
- `nimlab service scheduler <on|off>`: Run the job scheduler (heartbeat and jobs) inside the service, or not *(asks first)*
- `nimlab service boot`: Start the service when the device boots *(asks first)*
- `nimlab service run`: The supervisor itself (the service files run this; not for daily use) *(interactive)*

**Telegram**

- `nimlab telegram status`: Bot name, mode, allowlist, owner and pollers
- `nimlab telegram test`: Check the bot token with Telegram (getMe)
- `nimlab telegram set-token`: Enter the bot token from @BotFather (hidden) *(interactive)*
- `nimlab telegram allow --capture`: Add yourself: send /start to the bot within 2 minutes *(interactive)*
- `nimlab telegram allow <telegram-id>`: Add a numeric Telegram ID to the allowlist *(asks first)*
- `nimlab telegram mode <polling|webhook>`: How the bot gets messages *(asks first)*
- `nimlab telegram voice <on|off>`: Answer voice notes with a voice note *(asks first)*
- `nimlab telegram refusal [<text>]`: Show or set the reply strangers get
- `nimlab telegram start`: Start the bot in the background (outside the service)
- `nimlab telegram stop`: Stop the background bot *(asks first)*
- `nimlab telegram run`: Run the bot in this terminal (Ctrl+C stops) *(interactive)*

**MCP**

- `nimlab mcp show`: MCP URL, key source and auth style
- `nimlab mcp test`: Connect to the MCP server and count its tools
- `nimlab mcp tools`: List every tool the MCP server offers
- `nimlab mcp set-url <url>`: Set the MCP server URL *(asks first)*
- `nimlab mcp auth <style>`: Set the auth style: x-api-key, bearer, header or none *(asks first)*
- `nimlab mcp menu`: The MCP menu *(interactive)*

**Memory**

- `nimlab memory show`: Memory settings and record counts
- `nimlab memory status`: Backend, connection and queue in one screen
- `nimlab memory test`: Connect, write, search and clean up a test memory *(real requests)*
- `nimlab memory list`: The newest memories
- `nimlab memory recall <query>`: Search memories the way a reply would (vector + keyword) *(real requests)*
- `nimlab memory add <text>`: Save a memory now (Telegram /remember); pins "my name is ..." *(real requests)*
- `nimlab memory identity`: Facts pinned about you (name, etc.): show, set <key> <value>, forget <key>
- `nimlab memory set <setting> <value>`: Change one memory setting (e.g. auto_store on) *(asks first)*
- `nimlab memory use <backend>`: Pick the backend: local, oracle, ords or auto *(asks first)*
- `nimlab memory embed <provider> <model>`: Pick the embedding model *(asks first)*
- `nimlab memory setup`: Guided memory setup *(interactive)*
- `nimlab memory menu`: The memory menu *(interactive)*
- `nimlab memory creds`: Enter the Oracle wallet login *(interactive)*
- `nimlab memory ords show`: Show the ORDS connection (no secrets)
- `nimlab memory ords login`: Enter the ORDS login (hidden) *(interactive)*
- `nimlab memory pending`: Memories waiting for an embedding
- `nimlab memory embed-pending`: Embed the waiting memories now *(real requests)*
- `nimlab memory flush-queue`: Write queued memories to the backend now
- `nimlab memory reembed`: Embed every memory again with the current model *(real requests, asks first)*
- `nimlab memory reembed --recreate`: Rebuild the vector column, then embed everything again *(real requests, asks first)*
- `nimlab memory forget <id>`: Delete one memory *(asks first)*
- `nimlab memory prune`: Delete old, low-importance memories *(asks first)*
- `nimlab memory sql <query>`: Run a read-only SQL query on the memory tables
- `nimlab memory load-onnx`: Load the in-database ONNX embedding model *(asks first)*

**Benchmarks**

- `nimlab bench router`: Router benchmark: routing accuracy and timings *(real requests)*
- `nimlab bench router --compare`: Router benchmark with the router off for comparison *(real requests)*
- `nimlab bench router --call`: Router benchmark on the voice-call path *(real requests)*
- `nimlab bench router --show`: Show the last router benchmark

**Tests**

- `nimlab test`: List the tests, one per part of the lab
- `nimlab test <name>`: Run one test (e.g. memory-recall, mcp, tunnel, telegram)
- `nimlab test all`: Run every test and print a pass / fail table *(real requests)*
- `nimlab test history`: The last test runs

**Scheduler and heartbeat**

- `nimlab jobs list`: Every job: on/off, next run, last result
- `nimlab jobs show <name>`: One job in full, with its recent runs
- `nimlab jobs create <name> --schedule <spec> --do <action>`: Create a job (schedule: FREQ=MINUTELY;INTERVAL=30, a cron, or 'at YYYY-MM-DD HH:MM'; --type quill_prompt, nimlab_command, test, mcp_tool, shell or chain)
- `nimlab jobs edit <name> --schedule <spec>`: Change a job (any --option of create)
- `nimlab jobs run <name>`: Run a job once now *(real requests)*
- `nimlab jobs enable <name>`: Turn a job on
- `nimlab jobs disable <name>`: Turn a job off (its history stays)
- `nimlab jobs delete <name>`: Delete a job *(asks first)*
- `nimlab jobs history [name]`: Run history: status, time, bug IDs
- `nimlab jobs next <name>`: The next run times
- `nimlab jobs audit`: Every change to jobs and suggested actions, with who made it
- `nimlab jobs tools`: The MCP tools the server offers now, to pick for a prompt task
- `nimlab jobs free-time --tools a,b`: Ready-made hourly Free time job with the tools you pick
- `nimlab heartbeat status`: Heartbeat on/off, next run, limits, the last report
- `nimlab heartbeat run-now`: One heartbeat now: Quill decides and acts *(real requests)*
- `nimlab heartbeat enable`: Turn the heartbeat on
- `nimlab heartbeat disable`: Turn the heartbeat off
- `nimlab heartbeat schedule <spec>`: How often the heartbeat runs
- `nimlab heartbeat actions`: The suggested actions (list, show, add, edit, remove, enable, disable)
- `nimlab heartbeat reports`: The last heartbeat reports: taken, skipped, why, where results went
- `nimlab heartbeat set <max_actions|token_budget|time_budget_sec|escalate_failures_to> <value>`: Heartbeat limits
- `nimlab scheduler status`: Is the scheduler running, and anything wrong with the jobs
- `nimlab scheduler run`: Run the scheduler in this terminal (the service normally does)
- `nimlab scheduler menu`: The Scheduler menu (old) *(interactive)*
- `nimlab ui scheduler`: The Scheduler menu: on/off, add a job step by step, heartbeat *(interactive)*

**Bugs and doctor**

- `nimlab doctor`: Check settings, keys, memory, MCP, platform and service for problems
- `nimlab doctor --no-mcp`: Doctor without contacting the MCP server
- `nimlab doctor --quick`: Quick doctor: no memory round trip, MCP or platform
- `nimlab doctor --json`: Doctor results as JSON (what Telegram /health reads)
- `nimlab doctor --fix`: Safe repairs: stale pid files, file modes, bad URLs; backs up first, checks again *(asks first)*
- `nimlab ui health`: The Health & repair menu *(interactive)*
- `nimlab bugs list`: Grouped error reports with bug IDs
- `nimlab bugs show <bug-id>`: One bug report in full (redacted)
- `nimlab bugs tail`: The newest bug log lines
- `nimlab bugs status`: Bug log size and retention
- `nimlab bugs prune`: Remove expired bug reports now *(asks first)*
- `nimlab bugs clear`: Delete every bug report *(asks first)*
- `nimlab report`: Write a support report (no secrets)
- `nimlab data overview`: What the data folder holds
- `nimlab data show <view>`: One data view (history, runs, ...)
- `nimlab data paths`: Where each data file lives
- `nimlab data migrate`: Move old data files into the current layout *(asks first)*

**Self-admin**

- `nimlab selfadmin status`: Self-admin on or off, shell access and the key
- `nimlab selfadmin on`: Let admins have the lab inspect and change its own setup *(asks first)*
- `nimlab selfadmin off`: Turn self-admin off *(asks first)*
- `nimlab selfadmin shell <on|off>`: Allow shell commands for self-admin, or not *(asks first)*
- `nimlab selfadmin others-read <on|off>`: Let non-admins read status, or not *(asks first)*
- `nimlab selfadmin fixes`: Fixes self-admin can apply
- `nimlab selfadmin audit`: What self-admin changed, newest first
- `nimlab selfadmin undo`: Undo the last self-admin change *(asks first)*

**Other**

- `nimlab commands`: This list
- `nimlab commands <area>`: One group of this list (setup, keys, models, server, ...)
- `nimlab help`: Same as commands
- `nimlab troubleshoot`: Symptoms and what to run for each
- `nimlab troubleshoot <symptom>`: The steps for one symptom
- `nimlab colors`: Colour test and settings
- `nimlab colours`: Same as colors

**The tests** (`nimlab test <name>`, or the Tests menu)

- `platform`: Platform: Python, venv, ffmpeg, cloudflared, linger, RAM/swap
- `key`: NVIDIA key present
- `catalog`: Model catalog reachable *(real requests)*
- `roles`: Router and persona roles answer (one short call each) *(real requests)*
- `grpc`: gRPC function IDs (ASR/TTS check) *(real requests)*
- `tts`: Speech: speak a test line *(real requests)*
- `asr`: Transcription: a synthetic tone *(real requests)*
- `embeddings`: Embeddings: one vector *(real requests)*
- `memory-backend`: Memory backend connection (Oracle, ORDS or local)
- `memory-write`: Memory write (and clean up) *(real requests)*
- `memory-recall`: Memory recall: write a marker, recall it, clean up *(real requests)*
- `mcp`: MCP: connect, list tools, one read-only call
- `server`: Local server self-test through the one model name *(real requests)*
- `tunnel`: Tunnel: /v1/models through the public URL with the server key
- `telegram`: Telegram: getMe, exactly one poller, owner set
- `service`: Service: supervisor running, children match the config, no strays
- `scheduler`: Scheduler: jobs parse, next runs, scheduler running
- `selfadmin`: Self-admin: key and audit folder
- `buglog`: Bug log writable
- `config`: Config lint
- `router`: Router: one turn through the real pipeline *(real requests)*

**Troubleshooting** (`nimlab troubleshoot <symptom>`)

- Telegram replies twice / duplicate bots (`telegram-twice`): `nimlab service status`, then `nimlab service cleanup`, then `nimlab telegram status`, then `nimlab test telegram`. Another phone, PC or an old install polling the same bot also causes this: stop it there.
- "Stray copies" in service status (`stray-copies`): `nimlab service status`, then `nimlab service cleanup`, then `nimlab service restart`, then `nimlab test service`. From 3.7.4 a second supervisor exits by itself; strays left by 3.7.3 need one cleanup.
- The server won't start or the port is busy (`port-busy`): `nimlab service status`, then `nimlab service cleanup`, then `nimlab serve info`, then `nimlab serve test`. Change the port with: nimlab serve settings port <n>
- The tunnel isn't reachable (`tunnel`): `nimlab serve tunnel status`, then `nimlab test tunnel`, then `nimlab service restart`, then `nimlab serve tunnel install`. A quick tunnel's URL changes on every start; a named tunnel keeps its hostname.
- MCP 401/403 or no tools (`mcp`): `nimlab mcp show`, then `nimlab mcp test`, then `nimlab mcp auth <style>`, then `nimlab mcp set-key`. Which tools appear is set in the MCP server's admin console.
- Memory isn't recalling (`memory`): `nimlab memory status`, then `nimlab test memory-recall`, then `nimlab memory recall <query>`, then `nimlab memory identity`, then `nimlab memory pending`, then `nimlab memory embed-pending`, then `nimlab memory set auto_recall on`
- A self-test check failed (`selftest`): `nimlab bugs list`, then `nimlab bugs show <bug-id>`, then `nimlab serve test`, then `nimlab doctor`. A timeout on the image-and-audio check is usually a slow model, not a dead port.
- A gRPC model fails (`grpc`): `nimlab grpc list`, then `nimlab grpc fill`, then `nimlab grpc check`, then `nimlab setup deps`
- After an update (`after-update`): `nimlab doctor`, then `nimlab service cleanup`, then `nimlab setup list`, then `nimlab test all`. The MCP URL and auth style live in the project folder: after a fresh install enter them again.
- A job or the heartbeat does not run (`scheduler`): `nimlab scheduler status`, then `nimlab jobs list`, then `nimlab jobs history`, then `nimlab service scheduler on`, then `nimlab test scheduler`. Times are in scheduler_settings.timezone (the system zone when empty).
- A full stop of everything (`stop-all`): `nimlab service telegram off`, then `nimlab telegram stop`, then `nimlab service stop`, then `nimlab service cleanup`, then `nimlab service status`. On Termux with termux-services, run `sv down nimlab` first, or runit starts it again.

<!-- END COMMAND REFERENCE -->

## Settings reference

Every setting, its default and what it does. config_cluster.json holds all of them except the server's,
which live in data/server_settings.json. Change them in the menus, with `./start.sh memory set <name> <value>`
for memory, or by editing the file; a running chat or service picks up changes on the next turn.
Passwords, client secrets and API keys never go in these files: they live in the credentials files
under ~/.config/nimlab (mode 600) or in env vars.

**Files and variables added in 3.8.2** (no new config_cluster.json settings): `~/.config/nimlab/endpoints.json`
(custom endpoints and their models, 600; `NIMLAB_ENDPOINTS` moves it), endpoint keys in
`~/.config/nimlab/secrets.json` (600; `NIMLAB_SECRETS` moves it; `NIMLAB_ENDPOINT_KEY_<NAME>` overrides one key for a run),
`data/backups/doctor-<time>/` (the settings backup `doctor --fix` makes first), and `NIMLAB_PLAY_TIMEOUT`
(seconds a local audio player may run before it is stopped, default 120, so a stuck player never hangs a call or a script).

### http_settings

In config_cluster.json.

- `http_settings.timeout_sec` (default `60`): Time limit for one model API call.
- `http_settings.retries` (default `2`): Retries for a failed model API call (429 / 5xx / network).
- `http_settings.backoff_sec` (default `1.5`): Wait before the first retry; doubles each time.

### voice_settings

In config_cluster.json.

- `voice_settings.voice_name` (default `"Magpie-Multilingual.EN-US.Aria"`): The TTS voice sent to Magpie / Riva.
- `voice_settings.auto_tts` (default `false`): Speak every terminal chat reply aloud.
- `voice_settings.language` (default `"en-US"`): Language code for TTS and ASR.
- `voice_settings.tts_url` (default `"https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation....`): The TTS endpoint (NVCF Magpie by default).
- `voice_settings.voice_profiles` (default `["Magpie-Multilingual.EN-US.Aria", "Magpie-Multilingual.E...`): Voices offered in the voice menu.
- `voice_settings.fast_route` (default `true`): A casual spoken turn goes straight to the persona: no router call, no reasoning call.
- `voice_settings.fast_route_max_words` (default `60`): Spoken turns longer than this still go through the router.
- `voice_settings.router_timeout_sec` (default `4`): The router's time limit on a voice turn (the text limit is routing_settings.router_timeout_sec).
- `voice_settings.turn_timeout_sec` (default `45`): Cap on every model call (ASR, router, persona, TTS) during a voice call turn.
- `voice_settings.slow_turn_sec` (default `20`): A voice turn slower than this goes to the bug log with its stage times (0 = never).
- `voice_settings.show_stages` (default `true`): Print the per-stage time line (record, convert, ASR, router, recall, persona, TTS, play, store) under each voice reply.

### mcp_settings

In config_cluster.json.

- `mcp_settings.enabled` (default `false`): Use the MCP server's tools in chat.
- `mcp_settings.url` (default `""`): The MCP endpoint URL.
- `mcp_settings.auth.style` (default `"x-api-key"`): How the key is sent: x-api-key, bearer, header (custom header_name) or none.
- `mcp_settings.auth.header_name` (default `"X-API-Key"`): Header name for the header style.
- `mcp_settings.auth.key_env` (default `"MCP_API_KEY"`): Env var that holds the MCP key (a typed key is kept in ~/.config/nimlab).
- `mcp_settings.protocol_version` (default `"2025-06-18"`): MCP protocol version sent in initialize.
- `mcp_settings.allowed_tools` (default `[]`): Optional local override: empty or \* = every tool the server exposes (tool access is set in the MCP server's admin console); names = only those.
- `mcp_settings.blocked_tools` (default `[]`): Optional local override: tool names never offered here.
- `mcp_settings.dedicated_endpoint` (default `"auto"`): auto / on / off: the URL is this agent's own endpoint (/mcp-<agent>, /mcp/<agent>, /<agent>/mcp, /<agent>-mcp). Shown in the summary only.
- `mcp_settings.own_memory_tool` (default `""`): This agent's own *_mem tool on the server (empty = guessed from the agent name).
- `mcp_settings.confirm_tool_calls` (default `false`): Ask before every tool call.
- `mcp_settings.max_tool_steps` (default `4`): Most tool rounds in one turn; then the model gives a final answer without tools.
- `mcp_settings.max_calls_per_step` (default `3`): Most tool calls run from one model reply.
- `mcp_settings.tool_timeout_sec` (default `20`): Time limit for one MCP tool call.
- `mcp_settings.max_result_chars` (default `8000`): A tool result longer than this is cut before it reaches the model.
- `mcp_settings.max_response_bytes` (default `1000000`): Largest MCP HTTP response read.
- `mcp_settings.tools_ttl_sec` (default `600`): How long the MCP tool list is reused before it is fetched again (v3.8.3; it is also fetched again after an MCP error).

### memory_settings

In config_cluster.json.

- `memory_settings.recall_top_k` (default `6`): How many memories recall adds before the persona answers (1-20; 3 before 3.8.0). A config still on the old 3 is moved to 6 once on the first 3.8.0 start; a value you chose is kept.
- `memory_settings.similarity_threshold` (default `0.45`): Lowest similarity a recalled memory needs (the recall trace shows the best scores under it).
- `memory_settings.rerank_candidates` (default `16`): How many vector and keyword hits are pooled for ranking and the reranker (10 before 3.8.0).
- `memory_settings.recent_on_recall_ask` (default `3`): When the user asks what you remember, or an identity question ("what's my name", "who am I", "what did I tell you"), also add this many recent memories.
- `memory_settings.hybrid_recall` (default `true`): Automatic recall runs keyword search (Oracle Text, FTS5 or a word scan) beside vector similarity and ranks both together. false = vector only.
- `memory_settings.hybrid_keyword_weight` (default `0.6`): Weight of the keyword list in the combined ranking (the vector list counts 1.0).
- `memory_settings.exclude_context_turns` (default `true`): Leave out recalled turns that are already in the conversation's short-term context.
- `memory_settings.recall_max_chars` (default `2400`): Most characters of recalled memories put in front of the persona per turn (each memory is cut at 800; 0 = no limit).
- `memory_settings.recall_version` (default `380`): Set by 3.8.0 after it moved the old recall defaults; leave it alone.
- `memory_settings.search_threshold` (default `0.3`): The built-in memory_search tool's lowest score.
- `memory_settings.trace` (default `true`): Show recalled memories, scores, k and the threshold in the trace.
- `memory_settings.long_term.backend` (default `"auto"`): auto / off / json / local / oracle / ords. auto: the Oracle wallet login if found, else ORDS, else the json file.
- `memory_settings.long_term.scope` (default `"shared"`): shared (every client shares one memory) or user (memories tagged per client id).
- `memory_settings.long_term.auto_store` (default `true`): Save each finished turn after the reply, on every channel (terminal, voice, endpoint, Telegram).
- `memory_settings.long_term.auto_recall` (default `true`): Recall related memories before the persona answers, on every channel.
- `memory_settings.long_term.owner_user` (default `""`): scope user: the id the terminal chat, voice calls and requests without a user share.
- `memory_settings.long_term.protected_profiles` (default `[]`): Extra profile names this agent may never use (the other agents' names are built in).
- `memory_settings.long_term.memory_search_tool` (default `"auto"`): auto / on / off: the built-in memory_search tool (semantic, keyword or both, with rerank).
- `memory_settings.long_term.pin_identity` (default `true`): Pin self-introductions ("my name is ...", "call me ...", "I live in ...") as identity facts per user and show them to the persona every turn.
- `memory_settings.long_term.identity_cache_sec` (default `15`): Oracle and ORDS only: how long one lookup of the pinned facts is reused.
- `memory_settings.long_term.identity_backfill_scan` (default `300`): How many stored memories are scanned once for introductions saved before 3.8.0.
- `memory_settings.long_term.store_mode` (default `"salient"`): all, salient (facts, preferences, decisions) or facts.
- `memory_settings.long_term.min_chars` (default `12`): Turns shorter than this are not stored.
- `memory_settings.long_term.dedupe` (default `"exact"`): off, exact or semantic: skip storing a turn already saved.
- `memory_settings.long_term.dedupe_threshold` (default `0.95`): Similarity above which a semantic duplicate is skipped.
- `memory_settings.long_term.retention_days` (default `0`): Memories older than this are pruned (0 = keep forever).
- `memory_settings.long_term.max_records` (default `0`): Oldest memories are pruned above this count (0 = keep all).
- `memory_settings.long_term.retry_after_sec` (default `60`): After the backend goes offline, wait this long before reconnecting.
- `memory_settings.long_term.local.directory` (default `""`): Folder for the local backend (empty = data/ltm).
- `memory_settings.long_term.embedding.provider` (default `"role"`): role, nvidia, openai, ollama, sentence_transformers or oracle (in-database ONNX).
- `memory_settings.long_term.embedding.url` (default `""`): Embedding endpoint URL (empty = the provider's default).
- `memory_settings.long_term.embedding.model` (default `""`): Embedding model; it must return as many dimensions as the table (nvidia/llama-3.2-nv-embedqa-1b-v2 returns 2048).
- `memory_settings.long_term.embedding.dimensions` (default `0`): Expected vector size (0 = whatever the model returns); checked against the table before storing.
- `memory_settings.long_term.embedding.send_dimensions` (default `false`): Also send dimensions in the request (models with selectable sizes).
- `memory_settings.long_term.embedding.api_key_env` (default `""`): Env var with the embedding key (empty = the NVIDIA key).
- `memory_settings.long_term.embedding.timeout_sec` (default `30`): Time limit for one embedding call.
- `memory_settings.long_term.embedding.query_prefix` (default `""`): Text put before recall queries (models that want a prefix instead of input_type).
- `memory_settings.long_term.embedding.passage_prefix` (default `""`): Text put before stored passages.
- `memory_settings.long_term.embedding.device` (default `""`): sentence_transformers device (cpu, cuda).
- `memory_settings.long_term.max_chars` (default `2000`): Longest text stored for one turn.
- `memory_settings.long_term.oracle.schema` (default `"MEM"`): Schema that holds the memory tables (MEM).
- `memory_settings.long_term.oracle.table_prefix` (default `"TESTBED"`): Table prefix: <prefix>_MEMORIES and <prefix>_META.
- `memory_settings.long_term.oracle.profile_id` (default `"TESTBED"`): Memory profile (AGENT_ID) in MEM; default TESTBED. Other agents' names are refused.
- `memory_settings.long_term.oracle.register_profile` (default `true`): Register the profile in MEM.AGENT_PROFILES during memory setup.
- `memory_settings.long_term.oracle.credentials_file` (default `"~/.config/nimlab/oracle_mem.json"`): Wallet backend login file outside the project (mode 600).
- `memory_settings.long_term.oracle.user` (default `""`): Wallet backend: database user (the password is only in the credentials file or env).
- `memory_settings.long_term.oracle.dsn` (default `""`): Wallet backend: the TNS alias or connect string.
- `memory_settings.long_term.oracle.config_dir` (default `""`): Wallet backend: folder with tnsnames.ora.
- `memory_settings.long_term.oracle.wallet_dir` (default `""`): Wallet backend: wallet folder.
- `memory_settings.long_term.oracle.index` (default `"ivf"`): Vector index: ivf, hnsw or none.
- `memory_settings.long_term.oracle.distance` (default `"COSINE"`): Vector distance: COSINE, DOT or EUCLIDEAN.
- `memory_settings.long_term.oracle.target_accuracy` (default `90`): Approximate search target accuracy (percent).
- `memory_settings.long_term.oracle.onnx_model` (default `""`): In-database ONNX embedding model (embedding.provider oracle).
- `memory_settings.long_term.oracle.dims` (default `0`): Vector size of the table column, VECTOR(n) (0 = any size).
- `memory_settings.long_term.oracle.query_prefix` (default `""`): Text put before recall queries when the database embeds them (e.g. bge's "Represent this sentence for searching relevant passages: "); stored memories are embedded without it.
- `memory_settings.long_term.oracle.connect_timeout_sec` (default `15`): Wallet backend connect time limit.
- `memory_settings.long_term.oracle.text_index` (default `true`): Oracle Text index for keyword search (falls back to INSTR).
- `memory_settings.long_term.ords.base_url` (default `""`): ORDS backend (same tables and profile as oracle): the schema's REST root, e.g. https://host/ords/mem. HTTPS only.
- `memory_settings.long_term.ords.auth` (default `"basic"`): ORDS backend: basic (database user and password) or oauth (client credentials).
- `memory_settings.long_term.ords.user` (default `""`): ORDS backend: the REST-enabled database user for basic sign-in.
- `memory_settings.long_term.ords.client_id` (default `""`): ORDS backend: the OAuth client id (the secret is only in the credentials file or env).
- `memory_settings.long_term.ords.credentials_file` (default `"~/.config/nimlab/ords_mem.json"`): ORDS backend login file outside the project (mode 600), written by `memory ords login`.
- `memory_settings.long_term.ords.timeout_sec` (default `20`): ORDS backend: time limit for one HTTPS request.

### agent_settings

In config_cluster.json.

- `agent_settings.name` (default `""`): Optional custom agent name shown in chat; other agents' names are refused.

### ui_settings

In config_cluster.json.

- `ui_settings.color` (default `"auto"`): auto / on / off: terminal colours (NO_COLOR and NIMLAB_COLOR also work).
- `ui_settings.color_depth` (default `"auto"`): auto / 16 / 256 / 24 (truecolor).

### guard_settings

In config_cluster.json.

- `guard_settings.check_input` (default `false`): Check user messages with the safety guard role.
- `guard_settings.check_output` (default `false`): Check replies with the safety guard role.
- `guard_settings.block_on_unsafe` (default `true`): Block a message the guard calls unsafe (otherwise only warn).
- `guard_settings.translate_target` (default `"English"`): Default target language for the translation role.

### routing_settings

In config_cluster.json.

- `routing_settings.use_intent_router` (default `true`): Use the intent router model to pick the role for each turn.
- `routing_settings.show_route` (default `true`): Print which role answered and why.
- `routing_settings.reasoning_gate` (default `true`): Reasoning only for long or explicit analysis turns.
- `routing_settings.reasoning_min_chars` (default `4000`): Message plus attached text at least this long may use reasoning.
- `routing_settings.reasoning_keywords` (default `true`): Explicit asks (analyze, plan, step by step, think deeply) may use reasoning.
- `routing_settings.chat_fast_path` (default `true`): Short small-talk text turns skip the router.
- `routing_settings.chat_max_words` (default `16`): Longest text turn the chat fast path accepts.
- `routing_settings.router_timeout_sec` (default `8`): The router's time limit on a text turn; on timeout the rules decide.
- `routing_settings.environment_block` (default `true`): Add the live ENVIRONMENT section (memory, tools, channel, voice rules) to the persona, reasoning and coding prompts every turn.
- `routing_settings.migrate_prompts` (default `true`): Once, remove instructions for tools that don't exist (like quill_mem) from config_system_prompts.json, after a backup.
- `routing_settings.fallback_enabled` (default `true`): When a role's model fails (429, any 5xx, a timeout) after its retries, try fallback models (v3.8.3).
- `routing_settings.fallback_to_reasoning` (default `true`): The persona's first fallback is the Reasoning role's model, with the persona's prompt and soul.
- `routing_settings.fallback_cooldown_sec` (default `300`): After a fallback answered, the primary model rests this long before it is tried first again.

### discovery_settings

In config_cluster.json.

- `discovery_settings.page_ttl_hours` (default `72`): How long a downloaded catalog page is reused.
- `discovery_settings.spec_ttl_hours` (default `72`): How long a downloaded API spec is reused.
- `discovery_settings.probe_workers` (default `3`): How many models `sweep` probes at the same time.
- `discovery_settings.probe_timeout_sec` (default `20`): Time limit for one sweep probe.
- `discovery_settings.probe_rpm` (default `30`): Requests a minute for the setup 200-OK sweep and the spec rebuild, so they stay under NVIDIA's free-tier limit; a 429's Retry-After pauses every worker. `NIMLAB_SWEEP_RPM` overrides it; 0 turns pacing off (v3.8.3).
- `discovery_settings.host_delays_sec` (default `{"build.nvidia.com": 10, "docs.api.nvidia.com": 3, "api.n...`): Seconds between requests to each host while crawling.
- `discovery_settings.include_retired_in_sweep` (default `false`): Also probe models the catalog marks as retired.
- `discovery_settings.playground_uses_catalog` (default `true`): Let the playground pick models from the downloaded catalog.

### judge_settings

In config_cluster.json.

- `judge_settings.judges` (default `["mistralai/mistral-large-4-1t-a52b", "nvidia/nemotron-3-...`): Models that score candidates in `judge`.
- `judge_settings.repeats` (default `1`): Times each candidate is judged.
- `judge_settings.judge_temperature` (default `0.0`): Temperature for the judges.
- `judge_settings.max_candidates_per_type` (default `16`): Most candidates judged per role type.
- `judge_settings.execute_generated_code` (default `true`): Run generated code (sandboxed, time-limited) when judging coding models.
- `judge_settings.code_timeout_sec` (default `10`): Time limit for running generated code.
- `judge_settings.entity_combos` (default `[]`): Role combinations to compare as whole entities.
- `judge_settings.candidate_overrides` (default `{}`): Per-model request overrides while judging.

### telegram_settings

In config_cluster.json (`./start.sh telegram`).

- `telegram_settings.allow` (default `[]`): Telegram user ids allowed to talk to the bot (the owner is always allowed).
- `telegram_settings.owner` (default `null`): Your Telegram user id.
- `telegram_settings.mode` (default `"polling"`): polling (one poller per bot) or webhook.
- `telegram_settings.refusal` (default `"polite"`): polite (reply to strangers) or ignore (say nothing).
- `telegram_settings.voice_replies` (default `false`): Answer voice notes with a voice note.
- `telegram_settings.username` (default `""`): The bot's @name, saved when it starts.
- `telegram_settings.admin_for_owner` (default `true`): The owner may run admin commands from Telegram.
- `telegram_settings.set_commands` (default `true`): Register the command menu with Telegram (setMyCommands) on every bot start: a default menu and the owner's full menu (v3.8.1).
- `telegram_settings.inline` (default `"owner"`): Inline mode (`@bot question` in any chat): owner, allowlist or off (v3.8.1). Turn inline on once in @BotFather with `/setinline`.
- `telegram_settings.inline_timeout` (default `8`): Seconds Quill gets for an inline answer before the result posts the question instead (v3.8.1).
- `telegram_settings.model_switch` (default `true`): The owner may switch the primary model and the exposed name with `/model` (v3.8.1); false makes `/model` view-only.

### service_settings

In config_cluster.json (`./start.sh service`).

- `service_settings.backend` (default `"auto"`): auto / termux / systemd / builtin: which supervisor keeps the server running (only one runs at a time).
- `service_settings.telegram` (default `false`): Run the Telegram bot under the service.
- `service_settings.scheduler` (default `true`): Run the job scheduler (heartbeat and jobs) under the service (v3.8.0).
- `service_settings.wake_lock` (default `true`): Take a Termux wake lock while the service runs.

### scheduler_settings

In config_cluster.json (v3.8.0; `./start.sh jobs`, `./start.sh scheduler`).

- `scheduler_settings.enabled` (default `true`): The scheduler starts at all; false makes `scheduler run` exit at once.
- `scheduler_settings.tick_sec` (default `20`): How often due jobs are checked, in seconds.
- `scheduler_settings.timezone` (default `""`): IANA time zone for schedules (America/Los_Angeles); empty = the system zone.
- `scheduler_settings.catchup` (default `"one"`): After downtime, for jobs with no catchup of their own: one (run once), none (skip, record MISSED), all (run each missed time).
- `scheduler_settings.catchup_max` (default `5`): catchup=all runs at most this many missed times.
- `scheduler_settings.max_parallel` (default `2`): Runs at once across all jobs; more wait for the next tick.
- `scheduler_settings.unlimited_job_tools` (default `true`): A quill_task job with its own tool list (Free time, email alerts) has no fixed tool-step cap: Quill may use those tools, and only those, as long as he likes, with runaway guards (`scheduler_settings.job_guard`) instead. `false` puts `mcp_settings.max_tool_steps` back on those jobs.
- `scheduler_settings.default_timeout_sec` (default `600`): Time limit for a run when the job sets none; longer is TIMED_OUT.
- `scheduler_settings.history_days` (default `30`): Run history older than this is pruned.
- `scheduler_settings.history_max` (default `2000`): Run history keeps at most this many runs.
- `scheduler_settings.output_chars` (default `1500`): Output kept per run in the history (redacted).

### heartbeat_settings

In config_cluster.json (v3.8.0; `./start.sh heartbeat`).

- `heartbeat_settings.max_actions` (default `3`): Suggested actions taken per heartbeat, at most (highest priority first).
- `heartbeat_settings.token_budget` (default `6000`): Rough tokens (characters / 4) per heartbeat for prompts and replies; no action starts past it.
- `heartbeat_settings.time_budget_sec` (default `600`): No new action starts after this many seconds.
- `heartbeat_settings.escalate_failures_to` (default `"telegram"`): A failed action's result also goes here: telegram, memory, log, or "" for nowhere.
- `heartbeat_settings.context_chars` (default `3500`): The fresh-context block Quill sees, at most this many characters.
- `heartbeat_settings.report_keep` (default `300`): Heartbeat reports kept.
- `heartbeat_settings.decision_max_tokens` (default `700`): Reply limit for Quill's decision step.

### server

In data/server_settings.json (`./start.sh serve settings`).

- `server.port` (default `8765`): Port of the local OpenAI-compatible endpoint.
- `server.bind` (default `"127.0.0.1"`): Listen address (127.0.0.1 = this phone only).
- `server.lan` (default `false`): Listen on 0.0.0.0 so the LAN can reach it.
- `server.model_prefix` (default `"testbed-"`): Prefix for the `testbed-agent` alias (accepted, not listed) and legacy debug names.
- `server.model_name` (default `"testbed"`): The one model name that serves the whole entity.
- `server.entity.client_system` (default `"append"`): append or ignore the client UI's own system message.
- `server.entity.trace` (default `"field"`): off, field (testbed_trace) or content (also under the reply).
- `server.entity.media` (default `"url"`): url (hosted /v1/files/<id>) or data (inline data: URLs).
- `server.entity.media_auth` (default `"link"`): link (unguessable id) or key (API key needed).
- `server.entity.media_ttl_hours` (default `24`): How long generated media stays downloadable.
- `server.entity.media_keep` (default `200`): Most generated media files kept.
- `server.entity.attach_max_chars` (default `20000`): Most characters of an attached document sent to the model.
- `server.entity.pdf_ocr_pages` (default `3`): Pages of a scanned PDF read with OCR.
- `server.entity.image_router` (default `true`): Let the router decide what to do with a picture.
- `server.entity.call_page` (default `true`): Serve the browser voice-call page.
- `server.log_requests` (default `true`): Write a request log line per call.
- `server.log_to_console` (default `true`): Also print request lines on the console.
- `server.self_test_timeout_sec` (default `90`): Seconds for each basic setup self-test check (models, chat, identity). A timeout is reported per check; setup offers continue / retry.
- `server.self_test_heavy_timeout_sec` (default `240`): Seconds for each heavy multimodal diagnostic (picture plus audio, image generation).
- `server.setup_full_self_test` (default `false`): Run the heavy multimodal diagnostics during setup (off: run them later with `serve test --full`).
- `server.cors_origin` (default `"*"`): CORS Access-Control-Allow-Origin value.
- `server.max_body_mb` (default `25`): Largest request body accepted.
- `server.stream_chunk_words` (default `3`): Words per streamed chunk when the reply was not streamed by the model.
- `server.agent_tool_calls` (default `"deny"`): deny or allow MCP tool calls for remote clients when confirm_tool_calls is on.
- `server.tunnel.tool` (default `"cloudflared"`): Tunnel program (cloudflared).
- `server.tunnel.mode` (default `"off"`): off, quick (trycloudflare.com) or named.
- `server.tunnel.auto_start` (default `false`): Start the tunnel with the server.
- `server.tunnel.named.method` (default `"token"`): token, or credentials (tunnel id plus credentials file).
- `server.tunnel.named.tunnel` (default `""`): Named tunnel id or name.
- `server.tunnel.named.credentials_file` (default `""`): Named tunnel credentials file.
- `server.tunnel.named.hostname` (default `""`): Public hostname of the named tunnel.
- `server.bugs.enabled` (default `true`): Write grouped error reports with bug IDs (data/bugs/); secrets are redacted.
- `server.bugs.max_mb` (default `5`): Size cap for the whole bug log; the oldest archives go first.
- `server.bugs.keep_days` (default `14`): Bug reports not seen for this long are deleted (two weeks).
- `server.bugs.compress` (default `true`): gzip a full events file instead of keeping plain text.
- `server.bugs.max_event_kb` (default `64`): One occurrence is cut to this size.
- `server.bugs.trace_in_request_log` (default `true`): Copy the short routing trace into each request-log line.
Legacy (v3.7.2): `server.expose.agent`, `server.expose.roles` and `server.expose.verified` are no longer settings. They have no default and are not in setup or the menu; a hand-set `expose.roles` / `expose.verified` in data/server_settings.json is still read and lists debug names beside the one model, and `expose.agent: false` is ignored.

<!-- settings-reference:end -->
