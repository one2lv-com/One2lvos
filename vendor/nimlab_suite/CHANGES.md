# Changes

## v3.8.6

Register a phone for the audio bridge from the launcher or setup and get one block to paste into Termux, and the build version in the launcher banner. This release also carries the 3.8.4 and 3.8.5 work, which ran live but never had a version of its own.

**Phone audio bridge setup (3.8.6).** Launcher **F Phone audio bridge** (also **P** on the Test server screen), `nimlab audio setup`, and an optional last step in `nimlab setup` (step 12, default Skip) all run the same flow: name the phone (checked: a-z, 0-9, - and _, not `all` or `active`; a name already registered offers a new key, another name, or cancel), say whether voice calls may use its mic, confirm the server address (the last one used, else the named tunnel's hostname), and Nim Lab registers it and prints its key once, then a block between `# ===== BEGIN NIMBRIDGE SETUP ...` and `# ===== END NIMBRIDGE SETUP ...` lines. Pasted into Termux on that phone, the block installs curl, jq and termux-api, writes the nimbridge script with a cat heredoc, checks it pasted cleanly (SHA-256), writes that phone's settings already filled in (`~/.config/nimbridge/config`, mode 600) and runs `nimbridge init`, which checks the key with the server, asks Android for the mic once when the mic is on, and starts the bridge. The phone asks nothing. The flow loops for more phones.

- The block is plain ASCII with no tabs, so a paste from a phone's SSH app works line by line in an interactive shell (tested on a pty with history expansion on). It runs inside one shell function, so a failed step stops it without closing Termux, and off Termux it changes nothing.
- The client has one source, `nimlab/clients/nimbridge.sh`; every block is built from it, so a client update reaches the next block printed.
- The key is shown on screen and inside the block by design and is written to no file or log on the server; only its hash is kept, as before. The instructions say the block holds that phone's key.
- `nimlab audio add NAME` still prints just the key. `nimlab audio add NAME --termux [--mic on|off] [--url URL]` prints only the block on stdout, for scripts.
- Giving an existing phone a new key keeps its label.
- nimbridge 1.1: new `nimbridge init` (no prompts; used by the block). `nimbridge setup` is unchanged, and phones on 1.0 keep working.

**Version in the banner (3.8.6).** The launcher's main banner reads `NVIDIA NIM TEST LAB v3.8.6`, taken from `nimlab/__init__.py` (`__version__`), the one place the version lives.

**Lab-wide audio bus (3.8.5).** `nimlab/audiobus.py`: Nim Lab on a headless VPS plays its audio (Telegram /autoplay, the terminal voice call, clips an agent publishes) on a phone's speaker through the nimbridge Termux client, and the phone's mic can feed a terminal voice call. Each phone has its own name and token (only the hash is stored); one phone is active at a time. Endpoints under `/v1/audio/bus`; commands `nimlab audio devices | add | remove | use | release | tone | say`.

**Scheduled jobs and latency (3.8.4).**

- Interrupts (`nimlab/interrupts.py`): a message from the user, a Gmail watchdog alert or another scheduled job ends an interruptible job (Free time).
- Job guard (`nimlab/jobguard.py`): a job with its own tool list has no fixed tool-step cap (`scheduler_settings.unlimited_job_tools`, default true), with runaway guards instead (the same failing call, identical repeated results, long failure runs, model backoff).
- MCP tool definitions are sent only when a turn needs a tool, not with every request.
- Long-term memory on Oracle can embed in the database with an optional search-query prefix.

## v3.8.3

MCP tools on every channel, prompt-task jobs with picked tools, model fallbacks, failed steps in bug reports, and a paced setup sweep.

**MCP tools on every channel (the FREE TIME bug).** Only terminal chat and doctor ever fetched the MCP tool list (`refresh_tools()`); a new `MCPClient` starts with no tools. Scheduler jobs, the heartbeat, the OpenAI server (Telegram, Telegram voice, inline, voice-call page) and a voice call opened straight from the menu therefore offered no MCP tools. `Entity.ensure_tools()` now loads the list on first use, on every path that builds a tool loop: thread-safe, cached for `mcp_settings.tools_ttl_sec` (600 s), refreshed after an MCP error, a 60 s back-off after a failed fetch, the reason kept for doctor. The MCP trace rows in the server's response now name the tool (they read a key the tool loop never wrote). With a coding role set, scheduled, heartbeat and prompt-task turns still let the persona use tools.

**Prompt task with tools (`quill_task`).** A prompt plus MCP tools picked for the job; only those are offered (or any tool, these preferred), with an optional "must call a tool" check. Scheduler menu 7 (own task) and 8 (ready-made hourly Free time job) with a paged multi-select picker over the live tool list; `nimlab jobs tools`, `nimlab jobs free-time --tools a,b`, `nimlab jobs create --tools a,b [--any-tool] [--require-tool]`; Telegram `/jobs tools` and `/jobs freetime a,b` (owner); Quill's self_jobs tool knows the type. Run reports list every tool called and how it went.

**Model fallbacks.** 429, any 5xx (including the upstream "content safety screening is temporarily unavailable" 503), timeouts and dropped connections, after the HTTP retries, go to the Reasoning model with the persona prompt (persona), then the role's secondary list (roles menu R, then F), then a cooldown before the primary is tried first again. Logged to `data/fallbacks.jsonl`; shown in doctor and `/health`. When every model fails Telegram names the cause in plain words instead of "server 502: ... HTTP 503".

**Failed steps in the trace and bug record (B-894BF1).** The failing persona step was missing from the trace, so the report only showed the router. Every failed attempt now carries role, model, upstream host/path (no keys), status, a short body, attempts and the fallbacks tried.

**Paced sweep.** The 200-OK sweep and spec rebuild are paced to `discovery_settings.probe_rpm` (30 a minute; `NIMLAB_SWEEP_RPM`), honouring Retry-After.

**Updating from git.** `cd <your clone> && git pull && bash update.sh`; nothing depends on the folder's name.

**New tests.** `tests/test_v383.py`: a fresh Entity with a fake MCP server calls a tool on its first turn on each channel (terminal, Telegram owner and guest, voice, server, scheduler quill_prompt, heartbeat, the full server path), caching/TTL/error refresh, a down server, concurrent first use, the coding-role rule; quill_task checks, only/any modes, must-call, missing and failing tools, the Free time template, a scheduler run end to end, CLI, menu picker and Telegram /jobs; fallbacks on 429/5xx and the exact safety-screening 503 body, order, cooldown, no fallback on 4xx, the plain-words message, the roles menu, doctor; the failed persona step in the trace and the bug record with its model and upstream host; the rate limiter, Retry-After and a paced prober.


## v3.8.2

Updating without a reinstall, custom endpoints, one routing path, health and safe repair, a rebuilt menu, and the fixes from the 4-AI audit of 3.8.1.

**update.sh (first release with it).** Unzip a release over the folder, then `bash update.sh`: it turns off auto-restart first (runit, systemd or the built-in supervisor), stops only this user's Nim Lab processes, waits for each to exit before forcing anything, starts the service once and runs the health check, printing GOOD TO GO only when every check passes. `--stop` and `--no-start`; a lock keeps two copies from running. Service & update > Clean restart runs the same steps. Keys, settings and memory are never touched.

- **Why cleanup needed 2-3 runs:** the supervisor was force-killed after 1.5 seconds, before it had stopped its children, and a runit-managed supervisor was never taken down, so runit restarted it. Cleanup now stops the respawner first and waits.
- **Scheduler:** creating a job from the commands menu split the "do" text into words and the job was refused; fixed. The menus and `jobs create` now say when the scheduler is not running and offer to start it.

**Custom endpoints (launcher A, `nimlab endpoints`).** Any OpenAI-compatible gateway: import its `/v1/models` list or type models in, put them on roles as `<name>:<model>`. Blank by default; keys in `~/.config/nimlab` (600); the NVIDIA key is never sent to a custom endpoint, and look-alike hosts are not matched.

**One routing path.** Chat, streaming, embeddings, rerank and image generation all go through `NimClient.route()`: a role's explicit URL, then a custom endpoint, then the registry. Unknown image models go to the image API instead of chat/completions (with a retry for strict schemas). TTS function IDs: the role's own ID, then verified/discovered/refreshed IDs, then the built-in table.

**Health & repair (launcher H).** `nimlab doctor --json`, `--quick` and `--fix`. `--fix` backs up the settings first, makes safe repairs only (file modes, stale pid files, settings that can never work), then checks again. New doctor checks: processes and locks, the Telegram poller lock (free / one poller / stale), an identity-pin round trip in the memory check (a throwaway fact, removed again), config integrity, file permissions and custom endpoints. Telegram `/health` (owner only) runs the quick check read-only; `/health full` runs everything.

**Telegram poller stale-lock reclaim.** When a poller died but a process it started still held the lock, no one polled and every start said another poller was running. A start now sees that the lock's owner is gone, stops the leftover (only a recognised Nim Lab process of this user; never a live poller or another program) and takes the lock: no 409 loops, never two pollers.

**Menus.** The launcher gains A Custom endpoints, U Service & update, W Scheduler, H Health & repair, E Tests and X Commands & troubleshooting. Result screens end with selectable next steps; the commands list shows short lines, 10 to a page; the heartbeat status screen has Turn on / Turn off.

**Audit fixes.**

- **start.sh TTS-injection test hang:** the test typed its hostile phrase at the NVIDIA key prompt (there was no key in the test), so the phrase became the "key" and a real network call was made, which stalled where packets are dropped. The key prompt now refuses anything with spaces or shell characters, the test runs offline in its own HOME, the voice synthesizer skips the audio player when no terminal is attached, and a local player that never returns is stopped after `NIMLAB_PLAY_TIMEOUT` seconds (default 120).
- `nimlab endpoints model` in the command list now marks `--kind` as optional, so running it from the Commands menu no longer asks for a literal `--kind`.
- The release zip is built by `tools/build_zip.py`: start.sh and update.sh keep mode 0755; no data/, output/, .git, caches or developer notes. (3.8.1 shipped `output/cache/specs`, 244 cached spec pages; the guided setup's functions step, or `nimlab sweep --plan-only`, rebuilds them.)

**New tests.** `tests/test_v382_finish.py` (/health, doctor --fix, custom endpoints, routing order and every caller via route(), the image fallback, TTS function-ID order, every new menu screen walked with colour on and off, heartbeat on/off, no suggested command missing from the Commands menu) and `tests/test_v382_audit.py` (Telegram concurrency on captured getUpdates fixtures: redelivery, two pollers at once, resume after restart, 409 handling; stale-lock reclaim with real processes; interrupt mid-poll then restart; hang-up mid-stream then server restart on the same port; Alex's cross-process memory contract for the JSON and local backends; packaging), plus the updater tests in `tests/test_v382_updater.py`.


## v3.8.1

The colour comes back to the new menus, and the Telegram rollout planned for 3.8.1.

**Colour in the 3.7.4 / 3.8.0 screens.** The Commands & troubleshooting menu, the troubleshooting guide, the tunnel test, the Tests menu, the Scheduler, Jobs, Heartbeat and Suggested actions menus, `nimlab jobs` / `heartbeat` / `scheduler` / `platform` / `commands` / `troubleshoot` / `test` output and the doctor Platform fix hints printed plain text ("== Title ==", "  1) ..."). They now use colors.py like the older menus: `C.header`, `C.rule`, `C.section`, numbered `C.entry` keys (letter keys too) and `C.ok` / `C.err` / `C.warn` / `C.dim` / `C.hint`. Test results: PASS green, FAIL red, skip yellow, bug IDs and next steps highlighted, the `*` live marker in yellow; the run-all table and the history rows coloured by verdict. New `nimlab/paint.py` colours finished lines for the terminal only: the plain line builders that Telegram, memory and Quill's tools read are unchanged. Colour turns off as before (not a terminal, `NIMLAB_COLOR=0`, `NO_COLOR`), and then the output is the same text as 3.8.0. Menus and long job lines fit `screen_width()` (a job line wraps to two lines on a phone). The Scheduler menu is also reachable from Commands & troubleshooting (`w`) and the launcher (hidden key `W`).

**Telegram rollout.**

- **The command menu sets itself.** On start the bot calls `setMyCommands` for the default scope (commands anyone allowed can use) and the owner's private chat (the full list, the same as the README's). BotFather `/setcommands` is no longer needed. `telegram_settings.set_commands: false` leaves the menu alone.
- **/model** shows the exposed model and the primary (persona) model; the owner can `/model primary <model id>` (checked against the verified / discovered lists) or `/model name <exposed name>`, each after a Switch / Cancel button, with an undo snapshot and an audit entry. `telegram_settings.model_switch: false` makes it view-only.
- **/remember <text>** saves a memory scoped to your Telegram user and pins "my name is ..." as an identity fact. New CLI `nimlab memory add <text> [--user ID]`.
- **/voice [on|off]** switches spoken replies; **/service** shows the status and **/service restart** asks first with a Restart button; **/cancel** drops the reply in progress.
- Replies now run off the polling thread (one at a time per chat), so `/cancel` and other commands answer at once while Quill is thinking. A new message while a reply is in progress replaces it.
- **Inline keyboards:** confirmations and `/heartbeat` (Run a heartbeat now, one on/off button per suggested action). Buttons carry one-time tokens only the asker can press; confirmations expire after ten minutes, heartbeat buttons after a day.
- **Inline mode:** `@Quill_svn_bot <question>` in any chat answers within `telegram_settings.inline_timeout` seconds (default 8), else posts the question as it is with a button to open the chat. Owner only unless `telegram_settings.inline` is `"allowlist"`; no admin tools. Needs `/setinline` in @BotFather once. `allowed_updates` now includes `callback_query` and `inline_query`.
- New settings: `telegram_settings.set_commands`, `inline`, `inline_timeout`, `model_switch`.
- Tests: `tests/test_v381_colors.py` (the new menus walked with colour forced on and off) and `tests/test_v381_telegram.py`.


## v3.8.0

The memory recall fix, a job scheduler with a heartbeat, Telegram slash commands with /autoplay, and everything from 3.7.4 (never released on its own: commands and Tests menus, Linux VPS support, fixes from the 3.7.3 install). Tested offline against fakes (no live NVIDIA, Oracle, ORDS, MCP or Telegram). Update with a fresh install; the steps are at the end.

**Memory recall fix.** "My name is SeVin" said on Telegram was saved, but a terminal call could not recall it: it ranked about third, behind an old "I do not remember who you are" answer and a turn already in the conversation, with only three memories recalled, and the recent-memory fallback only fired on "remember" phrasing.

- **Pinned identity facts.** Self-introductions ("my name is ...", "call me ...", "I'm SeVin", "I live in ...", "my birthday is ...", "my pronouns are ...") are stored as `identity` records per user and shown to Quill every turn, on every channel, as KNOWN FACTS ABOUT THE USER. A new value replaces the old one. Introductions saved by older versions are found and pinned once. `nimlab memory identity` shows, sets and forgets them; `long_term.pin_identity` turns it off.
- **Hybrid recall.** Vector similarity and keyword search (Oracle Text `CONTAINS` on the existing QUILL/TESTBED text index, `INSTR` without Oracle Text, FTS5 on the local store, a word scan on JSON and the offline queue) run side by side and are ranked together (reciprocal rank fusion), then reranked. Plain SQL, no stored procedures. `nimlab memory recall` uses the same ranking and shows how many came from each side.
- **Context turns left out.** Turns already in the conversation's short-term history no longer take recall places (`exclude_context_turns`).
- **Identity questions are memory questions.** "What's my name", "who am I", "what did I tell you", "do you remember me" also add the newest memories.
- **Never stored or recalled:** the setup self-test's requests (marked `X-Nimlab-Self-Test: 1`; its fixed prompts are recognized too) and Quill's own "I don't remember / I don't know who you are" answers. Ones already stored are skipped at recall.
- **More room.** `recall_top_k` 6 (was 3) and `rerank_candidates` 16 (was 10), within `recall_max_chars` 2400. A config still on the old defaults is moved once; values you chose are kept.
- **Two processes, one store.** The JSON and local stores pick up memories the Telegram bot wrote in the background. JSON reloads when the file changes and merges on every write under a file lock: nothing another process wrote is overwritten, and a deletion elsewhere stays deleted.
- New settings: `hybrid_recall`, `hybrid_keyword_weight`, `exclude_context_turns`, `recall_max_chars`, `long_term.pin_identity`, `identity_cache_sec`, `identity_backfill_scan` (README Settings reference).
- Tests: `tests/test_v380_recall.py`, including the exact live ranking, store on Telegram then recall in a terminal call, and a real second process writing for the JSON and local stores, on JSON, local and (fake) Oracle.

**Scheduler and heartbeat.**

- Jobs work like Oracle's scheduler: calendar strings (`FREQ=MINUTELY;INTERVAL=30`), cron lines or one-off `at` times; retries with doubling waits, a time limit, overlap limits, catch-up after downtime (one, none, all), broken after too many failures in a row, run history and an audit log of every change. Single instance; the service runs it as a child (`service scheduler on|off`). Doctor check and a "scheduler" system test.
- The heartbeat: a built-in job, off by default, every 30 minutes, with 4 suggested actions (health-check, bug-review, tunnel-recover, memory-digest). Quill decides which to take within limits on actions, tokens and time; each run writes a report.
- Result routing to Telegram, memory, the log, an MCP tool or nowhere: always, only on failure, or only when notable; a failed delivery goes to the log. Failures also go to Telegram.
- `nimlab jobs`, `nimlab heartbeat`, `nimlab scheduler` and a Scheduler menu. Quill gets admin tools for jobs and suggested actions; a scheduled run can read jobs but not change them, and deleting asks first.

**Telegram commands.** The phone's hand-patched `tgcmds.py` is now built in (`nimlab/tgcmds.py`), hooked in before the /start-/help check; a fresh install replaces the patched copy. `/status`, `/test`, `/roles`, `/recall`, `/mcp`, `/tunnel`, `/jobs`, `/heartbeat` (`/heartbeat run` for the owner), `/bugs`, `/logs`; `/model`, `/remember`, `/voice`, `/service`, `/cancel` answer "arrives in 3.8.1". The greeting still starts with "Hi! Send text, a photo or a voice note."

- **/autoplay [on|off|status]** (owner only; no argument switches it): Quill's voice replies also play on the phone speaker right after they are sent, through `termux-media-player`, else `play-audio`. State in `data/tg_autoplay.json`. It warns when no player is installed or spoken replies are off, says the phone speaker isn't available off Termux, and never breaks the voice reply.
- The README has the list to paste into @BotFather `/setcommands`, including `autoplay - Play voice replies on the phone speaker`.
- **Fixed: voice notes on Telegram failed** with "server 404: The model 'asr' does not exist or is not exposed by this test server". Since 3.7.2 the endpoint lists only the agent name, but the bot still asked for model `asr` (transcription) and `tts` (spoken replies). Both now send the exposed agent name, which the server maps to the ASR and TTS roles (the same change as the phone's sed patch). No other internal client sends a role name as the model; a test checks that. New regression test: a Telegram voice note in and a voice reply out against a server that exposes only the agent name.

## v3.7.4

A Commands & troubleshooting menu, a Tests menu, Linux VPS support (Oracle Cloud Always Free), and fixes from the 3.7.3 fresh install on the phone. Tested offline against fakes (no live NVIDIA, Oracle, ORDS, MCP, Telegram or Cloudflare calls; not run on the phone or a VPS).

- **Commands & troubleshooting (main menu H).** Every command by area with a one-line description, from one table checked against the argparse definitions. Pick one to run it: arguments are asked for, commands that stop, delete or change something ask first, and you come back to the list. A troubleshooting guide by symptom (Telegram replies twice, stray copies, port busy, tunnel unreachable, MCP 401/403 or no tools, memory not recalling, a failed self-test check, gRPC failures, after an update, a full stop) runs its steps one by one or all in order with a question before each. CLI: `nimlab commands [area]` (alias `nimlab help`) and `nimlab troubleshoot [symptom]`.
- **Tunnel test.** `GET <public URL>/v1/models` with the server's own key (read from its settings, never printed), reporting 200 with the model, 401 (key rejected), 530 / 1033 (tunnel down or URL stale) or DNS in plain words; optionally one short chat turn through the tunnel.
- **Tests (main menu E).** One test per part: platform, NVIDIA key, model catalog, roles, gRPC function IDs, TTS, ASR (synthetic tone), embeddings, memory backend, memory write, memory recall (marker written, recalled, removed), MCP (connect, list, one read-only call), local server self-test, tunnel, Telegram (getMe, exactly one poller, owner set), service (running, children match the config, no strays), self-admin, bug log writable, config lint, router (one turn). Each shows pass / fail / skip with the reason and time; a failure gets a bug ID and the next step with its troubleshooting entry; tests that send real requests are marked. `nimlab test`, `nimlab test <name>`, `nimlab test all` (table, exit 1 on a failure), `nimlab test history`. Runs are saved to `data/test_history.jsonl`. The tests reuse the existing checks.
- **README Command reference** generated from the same table (`python3 tools/update_readme_commands.py`); a test fails when it is stale. The README links to it near the top.
- **Linux VPS.** `start.sh install` handles PEP 668 (`externally-managed-environment` on Ubuntu 23.04+ / Debian 12): it makes a venv in `.venv` (or `~/.local/share/nimlab/venv`) and installs there, never with `--break-system-packages`; `start.sh`, the shortcut and the service then use the venv's Python. pip uses `--prefer-binary`. Install hints for apt, dnf and pkg (python3-venv, ffmpeg, cloudflared with Cloudflare's package repo); a missing cloudflared gives a clear message with the command for your system. New `nimlab platform` and a Platform section in `nimlab doctor` and the Tests menu: Python, venv, ffmpeg, cloudflared, systemd linger, root, RAM/swap (warns under 1.5 GB with no swap and prints the swapfile commands).
- **Off Termux** the terminal voice call says it needs Termux and does not start; the wake lock defaults off. Telegram voice notes still work.
- **systemd service on a VPS.** Install checks linger and prints `sudo loginctl enable-linger $USER` when it is off; running as root gets a warning. New `sudo nimlab service install --system`: a system-wide unit that runs as the sudo user, never as root.
- **Small boxes.** The 200 OK test scales its probe workers to RAM and CPU (at most 2 under 1.5 GB, 1 under 768 MB) and drops each page plan once probed.
- **Fix: extra supervisors.** The phone showed three idle supervisors after setup. A supervisor that cannot get the lock now exits after an 8-second grace (under runit after a further minute, so runit does not respawn it in a tight loop), logging one line an hour at most. `start.sh` execs Python instead of running it as a child, so `sv down` / `sv restart` signal the supervisor itself, and a supervisor whose runit wrapper died stops. Setup's service step sees a running service and does not start a second one; installing under termux-services when it already runs does not enable it again.
- **Fix: Telegram set up after the service step was not started.** The supervisor watches `config_cluster.json` and starts a part turned on after it started (and stops one turned off) without a restart. The Telegram step no longer restarts the service for it.
- **Fix: the summary said "tunnel off" while a quick tunnel ran.** The summary shows the configured mode and the real state: running with its URL, stopped, or "off (but a quick tunnel is running: <url>)".
- **Fix: the MCP auth label in the summary could be stale.** Every summary line is read again from the saved config when it is printed; the MCP step reads the auth style through one helper that accepts every form older versions wrote.

## v3.7.3

MCP tools are open by default: tool access is controlled in the MCP server's admin console, and the lab trusts it. Also fixes the setup MCP step showing the wrong auth style. Tested offline against fakes (no live NVIDIA, Oracle, ORDS, MCP or Telegram calls, not yet run on the phone).

- **No local tool filter by default.** The risky-tool filter is gone: no more name matching (`RISKY_TOKENS`), no blocking on the server's `destructiveHint` / `readOnlyHint` annotations, and no default block on other agents' `*_mem` tools. Every tool the endpoint lists is offered to the persona and the roles. To keep a tool away from Quill, switch it off for Quill's endpoint in the MCP server's admin console.
- **Optional local overrides.** `mcp_settings.allowed_tools` (empty or `["*"]` = every exposed tool; a list = only those) and the new `mcp_settings.blocked_tools` (never offered). Both default to empty. `own_memory_tool` is always allowed. Edit them in Settings > MCP > 9 or the testbed's MCP settings group.
- **No per-call confirmation by default.** `confirm_tool_calls` now defaults to off and asks before every call when on. `confirm_risky_tools` is removed: old configs still load; the first load drops it and turns `confirm_tool_calls` off (the old default asked before every call).
- **Short startup summary.** `[MCP] N tools from <url>, all available`, or the count left out by local overrides with the `blocked_tools` names. No per-tool list unless you ask: new `nimlab mcp tools`, `nimlab mcp test -v`, or `/tools` in chat.
- **Dedicated endpoints.** Detection recognises `/mcp/<agent>`, `/mcp-<agent>`, `/<agent>/mcp` and `/<agent>-mcp` (with `_` too), so `https://svn-dev.online/mcp-quill` is seen as Quill's own endpoint. The setup and menu hints show both `.../mcp-quill` and `.../mcp/quill`. It now only changes the summary text.
- **Auth style bug fixed.** In `nimlab setup mcp`, choosing "Authorization: Bearer" printed "Auth style set to bearer" but the After line said "auth x-api-key". The choice was saved correctly to `mcp_settings.auth.style`; the step's summary read a top-level `auth_style` field that is never written. The step's default answer read the same missing field, so pressing Enter on a rerun really did reset bearer to x-api-key. Both now read `auth.style`, and the summary shows the custom header name for the header style. New tests check that each style (x-api-key, bearer, header, none) is saved and shown, that a rerun keeps bearer, and that the connection test sends the chosen header.
- The persona's environment block no longer says other agents' memory tools "are not yours" when the endpoint lists them.
- README: "Tool safety" is now "Tool access", and the settings reference covers `blocked_tools` and the new defaults. Version 3.7.3 everywhere.

## v3.7.2

First-run setup in the order SeVin asked for, one endpoint model, and a router benchmark. Tested offline against fakes (no live NVIDIA, Oracle, ORDS or Telegram calls, not yet run on the phone).

- **Setup order.** 1 NVIDIA key (dependencies and the `nimlab` shortcut now happen quietly right after it, so the key is the first question), 2 discover (API catalog + build.nvidia.com, with progress), 3 function IDs and specs (each model's build.nvidia.com page: endpoints, gRPC-only marks, NVCF function IDs, samples; no test requests), 4 the 200 OK test (full, faster or skip, each with a time limit; it fills any gRPC function ID still missing), 5 MCP, 6 roles, 7 gRPC review, 8 memory, 9 server (self-test, tunnel, service), 10 Telegram, 11 self-admin. `nimlab setup list` shows the new order; `nimlab setup <step>` works for every step under the new names, numbers and aliases (`deps` and `shortcut` still run on their own).
- **Missing data is named, never blamed on the key.** A step whose data comes from a skipped step says so ("No models discovered yet ...: run step 2") and offers to run it now. The 3.7.1 gRPC step said "No gRPC models known yet" and then "the refresh failed; check the NVIDIA key (step 3) and the internet" on a fresh install; it now says it is missing data and offers to read the model pages or run the 200 OK test. `nimlab grpc refresh` with nothing known says the same (exit 3). New `nimlab grpc fill`.
- **Roles from what answered.** The roles step suggests one model per role from the 200 OK list (or an MCP tool for MCP-capable roles such as TTS or image generation), keeps current choices that still pass, and offers accept all, change one (a numbered list of suited and possible models and tools, or any id) or keep.
- **Memory embeddings from the verified list**, each with its size against the VECTOR(2048) table.
- **Existing installs are not forced through discovery.** Data steps that already have results default to Skip and offer a refresh.
- **Ctrl+C in a long setup step** stops that step only; what it finished is kept.
- **`nimlab sweep --time-limit`**: a sweep cut short leaves the models it did not reach for the next run and never writes them as failures.
- **One endpoint, one model name.** `/v1/models` lists exactly one name (`model_name`, default `testbed`); chat, embeddings, rerank, speech, transcriptions and images all take that name and go to the right role inside. The `expose` switches are gone from setup, the settings menu (`serve settings roles/expose` explain why) and the defaults; an old default `expose` block is cleaned up on load, a hand-set one is still read as a legacy debug option.
- **Self-test through the one name.** Embeddings, rerank and speech are tested with the agent's model name, so a default install no longer SKIPs embeddings with "no embedding model exposed (set the Embedding role)" when the role is set. An unset role is a SKIP that names it: "the Embedding Model role isn't set: run `nimlab setup roles`". Setup still ends in the main menu, pass or fail.
- **Settings that cannot work are flagged** in setup and `nimlab doctor`: a `voice_settings.tts_url` (or `asr_url`) that is a website homepage such as `https://nvidia.com`, role models or fallbacks that are bare URLs, and role endpoints that are homepages.
- **Router benchmark.** `nimlab bench router [--runs N] [--call] [--only] [--prompt] [--compare] [--show]` and Benchmarks > Router: built-in prompts for every route through the testbed's own chat and call pipelines; per turn the route vs the expected one, router decision time, each HTTP call's bytes, time to first byte and total, memory time and end-to-end time with routing overhead apart from NVIDIA API time; median and p95 per route; saved to the benchmark history. HTTP calls now record their timings on the turn's tracker for this.

## v3.7.1

Fixes from testing 3.7.0 on the phone. Tested offline against fakes (no live NVIDIA, Oracle, ORDS or Telegram calls, not yet run on the phone).

- **Setup self-test no longer crashes on a slow model.** A timeout or dropped connection in any check is that check's FAIL with the reason and a bug ID; the test goes on. Basic checks (models, auth, chat, streaming, identity) are separate from the heavy live checks (picture + audio, image generation). Setup runs only the basic ones; `nimlab serve test` runs both (`quick` skips the heavy ones). The summary says which checks failed and whether the server is fine, instead of "is the port free?". New `self_test_timeout_sec` (90) and `self_test_heavy_timeout_sec` (240).
- **Tool calls from real models parse.** Several JSON objects in one `<tool_call>` block (MiniMax parallel calls, the "Extra data" rejection), JSON arrays, `"parameters"`, the OpenAI function shape, fenced JSON, MiniMax `<invoke>` XML, and native `tool_calls`.
- **No tool markup or template tokens in replies or speech.** Hermes/Qwen, MiniMax (`]<]minimax[>[`), Llama, gpt-oss, Mistral and DeepSeek markup is removed from replies and streamed tokens. At `max_tool_steps` the persona writes a real final answer with no tools.
- **TTS input is cleaned** (markup, brackets, code, links, control characters), with one strict retry on a Triton 400; a failed TTS leaves the reply as text.
- **Safe MCP tools by default.** An empty allowlist means no MCP tools. Other agents' `*_mem` tools and write/exec/send tools are always blocked unless named one by one, and named risky tools still ask before each call. Dedicated agent endpoints (`.../mcp/quill`) allow what the endpoint exposes. `own_memory_tool` for the entity's own memory tool. Startup shows tools exposed vs allowed. Settings > MCP can switch to a dedicated endpoint and test it with the full tool list.
- **Automatic long-term memory on every channel.** The terminal chat, voice calls, the endpoint and Telegram share one pipeline: semantic recall (`VECTOR_DISTANCE`) before the persona, store after the reply, through the direct DB connection, never MCP. "What were we talking about?" also brings the most recent memories. Trace lines show the backend, hits and milliseconds. The terminal, voice calls and requests with no `user` field share `owner_user`'s scope.
- **Built-in `memory_search` tool** (in-process, semantic / keyword / both, merged, de-duplicated, reranked). Keyword search uses an Oracle Text `CONTAINS` index made by `memory setup`, with an INSTR fallback; local uses SQLite FTS5.
- **Optional custom memory profile name** in setup (default stays TESTBED); other agents' profile names are protected.
- **ENVIRONMENT block** for the persona, reasoning and coding prompts, built from the live config each turn (memory, tools, abilities, channel and output rules; voice rules win over list-style guidance). **Prompt lint** at startup and in the doctor. **One-time migration** of `config_system_prompts.json` (with a backup) removes instructions to call tools that do not exist; shipped prompts no longer name tools.
- **`nimlab doctor`**: memory write + semantic recall + keyword search round trip through the wallet connection, prompt lint, MCP exposure and own-tool schema.
- **Bug log** (`nimlab bugs`): grouped, redacted error reports with bug IDs and automatic retention (the bugs folder stays under 5 MB, entries older than 14 days are deleted); per-stage timings and timeouts.
- **Setup retry and the main menu.** After a failed self-test, setup offers Retry or Continue. The first-run guided setup now always ends in the launcher's main menu, also when setup or its summary fails, and a background service that keeps setup's output pipe open no longer holds setup until its timeout.
- **One supervisor, one server, one Telegram poller.** A second supervisor (for example termux-services next to the built-in one) waits instead of starting a second server; the 5-minute crash-loop cooldown survives a supervisor restart; serve exits with 75 when another Nim Lab server holds its port and 78 when another program does, and the supervisor does not restart it. `service status` lists running children, restarts, last exit code and error line and stray copies; new `service cleanup` stops strays (offered by `service start`/`install`).
- **Telegram never answers one update twice.** One poller per bot (4 conflict errors in a row, HTTP 409, stop it with a config error). Every poller and the webhook claim each `update_id` in a shared, locked file (`data/telegram/last_update.json`) before answering, so duplicate pollers or an unconfirmed offset can no longer send the same /start greeting five times. The offset is kept across polls, confirmed (update_id + 1) when a poller or `telegram allow --capture` ends, and capture stops as soon as the owner is saved. When the service is already polling, capture asks it instead of starting a second poller (the old setup hang); it shows progress, ends at once on a 409, and offers to type the ID or skip. The bot's @name is saved.
- **Auto store / auto recall read one setting.** Setup, the memory menu, the header and every channel read `memory_settings.long_term` from `config_cluster.json`; the menu saves only what changed and a running chat or service picks changes up on the next turn. Setup asks about auto store and auto recall directly. The header counts the backend in use ("Oracle TESTBED: 4 (auto store off)").
- **Embeddings that explain themselves.** Every embedding call sends `input_type` (query for recall, passage for storing), truncation and the number format; a field the model rejects is retried once without it, never one it says is required. The memory test sends one query and one passage call and shows the HTTP status and the model's own error text. The vector size is checked against the table (VECTOR(2048)). A turn that cannot be embedded waits in a pending queue (found by keyword search, embedded later) instead of being dropped. Setup offers `nvidia/llama-3.2-nv-embedqa-1b-v2` (2048 dimensions). New `memory status|pending|embed-pending|reembed [--recreate]|embed models`. The recall trace shows each hit's score, k, the threshold and the best scores just under it.
- **ORDS memory backend.** The same MEM tables over HTTPS (ORDS), with a user and password or an OAuth client ID and secret, typed hidden and saved only in `~/.config/nimlab/ords_mem.json` (600). In setup, the memory menu (3o) or `nimlab memory ords login`; same vector search, keyword search and pending queue as the wallet backend.
- **Voice calls.** Each turn shows how long each stage took (recording, conversion, ASR, router, recall, persona, TTS, playback, store); slow or failed turns go to the bug log with those times. Casual spoken turns skip the router and reasoning; the router gets 4 s on a voice turn and each model call 45 s (both settable). The turn is stored after the reply starts playing. Text for TTS drops tool markup, template tokens and unpaired brackets or quotes (the HTTP 400).
- **Settings reference.** The README lists every setting with its default; a test fails when one is missing, and `config_cluster.json` carries every section.
- **Bug log redaction** now also removes a Telegram bot token inside a bot URL (`.../bot<token>/getUpdates`).
- Tests: new `test_v371*.py` suites (self-test, tool-call parsing, MCP policy, memory, embeddings, ORDS, voice, service, settings docs, Telegram duplicates, regressions: memory on every channel with one scope, setup retry/continue, bug-log cap, two-week expiry and redaction) and first-run-to-main-menu tests in `test_start_sh.py`.

## v3.7.0
Release of the v3.6.1 work-in-progress, finished and tested. Includes everything listed under v3.6.1 below.
- **Guided setup.** `nimlab setup` (launcher S, offered once on first launch): ten steps (dependencies, shortcut, NVIDIA key, MCP, gRPC, memory, roles, server, Telegram, self-admin), each showing its status before and after, skippable and re-runnable; `nimlab setup <step>` / `setup list`; a summary at the end. Oracle memory via a TLS connection string or a wallet, written to `~/.config/nimlab/oracle_mem.json` (600), with common Oracle errors explained. New module `nimlab/wizard.py`.
- **Server setup and Cloudflare tunnel.** Bind address, port, model name, endpoint key, CORS, streaming, trace, tool calls and logging, a local self-test, then local only / quick tunnel / named tunnel (token or tunnel ID + credentials file + hostname, config generated). Tokens are read hidden, stored with 600 permissions, passed to cloudflared in its environment and scrubbed from its output. cloudflared is installed when missing; a tunnel that dies is retried with growing delays while the server keeps running. `nimlab serve tunnel quick|named|off|status|auto on|off|install|token-delete`. New module `nimlab/tunnel.py`.
- **Keep running.** `nimlab service install|remove|start|stop|restart|status|logs|boot|telegram`: termux-services with a wake lock and optional Termux:Boot start on Termux, a systemd user unit on Linux, the lab's own supervisor elsewhere. Crashed parts restart with growing delays, a crash loop pauses for 5 minutes, logs rotate with secrets removed, service files hold no secrets. New module `nimlab/service.py`.
- **Telegram bot.** `nimlab telegram set-token|test|allow [--capture]|status|start|stop|mode|voice|refusal`: allowlist with owner capture, polite refusal or silence for others, long polling or a webhook with a secret header, same pipeline as /v1/chat/completions as `telegram:<id>`, voice notes to ASR, photos to vision, optional voice replies, typing indicator, 4096-character splitting, MarkdownV2 with plain fallback. New module `nimlab/telegram.py`.
- **Self-admin.** The testbed entity can read and change its own roles, settings, prompts, memory options and server settings, run jobs and control the service and tunnel, for admins only (terminal, admin key, Telegram owner). Secrets masked, snapshot before every change with undo, a yes in a later message for risky actions, an audit log, shell/file edits behind a separate switch (off by default). New module `nimlab/selfadmin.py`.
- **Parakeet / Riva ASR over gRPC by default.** Parakeet, Canary and Conformer ASR models use NVCF gRPC even before a scan marks them (fixes the HTTP 400 in voice calls); only your own server address or an explicit `http` setting keeps HTTP. Audio sent over HTTP is converted to 16 kHz mono WAV first (clear `pkg install ffmpeg` error if missing), and failed calls show NVIDIA's error text with a gRPC hint.
- **Reasoning only when it's needed.** Normal conversation, small talk, quick questions and status checks go straight to the persona with no reasoning-role call. Short everyday turns skip the intent router call too. The reasoning role runs only for long input (message plus attached text of at least `reasoning_min_chars`, 4000 by default) or an explicit planning, analysis, step-by-step or "think deeply" ask. New `routing_settings`: `reasoning_gate`, `reasoning_min_chars`, `reasoning_keywords`, `chat_fast_path`, `chat_max_words`, `router_timeout_sec`. The intent router has its own 8 s timeout. The route and its reason are in the trace (`route_reason`, request log, and a `route:` line in the terminal call). This fixes v3.6.0 voice turns such as "Let's see if this voice message is working now" waiting 61 s for the reasoning model.
- **Accurate failure reports.** When an ability fails or times out, the persona names which one failed and why (for example "the reasoning model timed out after 61s"), says which steps worked, and still answers the message. It no longer reports the user's request or the voice path as failing. The call latency line names each step (`Reasoning FAILED 61.0s`) where it used to say "other abilities". An unreachable memory store is reported once per outage, and a failed MCP call is reported as an MCP failure.
- **Fix offers.** After a failure, an admin is offered a concrete fix the testbed can make itself (`nimlab/fixes.py`): lower the timeout, switch to a verified model, refresh gRPC function IDs, switch memory to the local store, or run the MCP or memory test. Missing ffmpeg and bad keys get a hint instead of a fix. The new `self_apply_fix` tool applies a fix only after a yes in a later message from the same admin, with a snapshot (undo works) and audit-log entries. Non-admins get the report only. `self_admin.fix_suggestions` turns offers off; so does `nimlab selfadmin fixes off`.
- Fixes found while testing: a Telegram reply split inside a code block could exceed 4096 characters after the closing fence was added; voice-note replies showed `_underscores_` literally; a self-admin tool name sent by a non-admin was forwarded to the MCP server instead of refused, and a tool box built for an admin did not re-check the caller on each call; "oracle" in an error was read as an ACL problem; re-running a setup step needed an extra keypress; cloudflared's output pipe was not closed and a failed start could report before its last lines arrived; `load_cluster_config()` bound its default path at import.
- Tests: new offline suites `test_wizard.py`, `test_tunnel.py` (a fake cloudflared script), `test_service.py` (temp PREFIX/HOME, fake runner; Termux, systemd and built-in), `test_telegram.py` (fake Bot API), `test_selfadmin.py`, `test_routing_gate.py` (casual voice turn never touches reasoning, long analysis task does, failure report, fix offer, apply with snapshot, non-admin refused), plus the shared `tests/sandbox.py`. The old main-menu test that expected S to open Discover now expects the guided setup.

## v3.6.1
- **`nimlab` shortcut.** `./start.sh shortcut` installs a `nimlab` command that runs this folder's `start.sh` from any folder, passing every argument through (`nimlab grpc check`, `nimlab memory test`). It is a small wrapper script, not a symlink (start.sh finds its folder from its own path): `$PREFIX/bin/nimlab` on Termux with the Termux bash shebang, `~/.local/bin/nimlab` elsewhere (created if missing; prints the PATH line to add when needed). Running it again after the folder moved updates the path; a wrapper whose folder is gone says so. `shortcut status` (where it points, whether that still exists, PATH shadowing), `shortcut remove` (only its own wrapper), `shortcut install <name>` for another name, `--force` to replace an unrelated command of the same name (otherwise left alone with a warning), `--dir` for another folder. New module `nimlab/shortcut.py`.
- **Menus tidied.** Launcher main menu is now 1-9 under three headings (Run / Models / Setup) with 0 to exit: Testbed, Playground, Test server, Discover & sweep (now with the gRPC tools), Benchmark & judge (reports, fleet and the judge in one screen), Roles & data, Keys & MCP (the NVIDIA key and MCP settings in one screen, replacing the separate key screen and MCP letter), Memory, Tools (install, shortcut, voice synth, colours). The letter keys of earlier versions still work but are hidden. Duplicates removed (the 200 sweep and fleet lived in two places; "full server menu" became "Server settings").
- Testbed main menu grouped (Chat / Roles & models / Setup) with chat first; soul.md and role prompts merged into one "Persona & prompts" screen; voice clone moved next to the roles. Settings went from 17 numbered items to six groups (MCP server & tools, Voice, Memory, Guard & translate, Routing, Terminal colours), each a short screen of its own. Memory, gRPC and test-server menus use headings and numbers 1-n with no gaps (memory's T/S letters still work); the memory "Recall" item now also sets the rerank pool.
- **Phone-sized.** Menus, banners and separators follow the terminal width (capped at 70, the old layout); on a narrow screen the hints after each option are dropped and long values are cut with "..." instead of wrapping. The testbed banner shortens to "NIM ORCHESTRATOR TESTBED" when needed.
- `./start.sh memory menu` and `./start.sh grpc menu` open those menus directly. All existing commands are unchanged.
- Tests: `tests/test_shortcut.py` and `tests/test_menus.py` (offline, temp HOME/PREFIX); menu tests that matched the old option numbers were updated.

## v3.6.0
- **Server-side long-term memory.** The served `testbed` endpoint recalls and stores memory itself on every /v1/chat/completions (streaming too) and /v1/responses request, so every UI connected to it shares one continuous, persistent memory with no client setup. Optional per-client scope via the OpenAI `user` field or an `X-Testbed-User` header (`memory set scope user`). /health and the serve block show where memory lives and whether it is online.
- **Backends** (`./start.sh memory use ...`, testbed settings 17, launcher Y, `serve settings memory.<key> <value>`): `auto` (default: Oracle when a login is found, else data/memory.json), `json`, `local` (SQLite + in-process vector index in a directory you choose, default data/ltm/), `oracle`, `off`.
- **Oracle 26ai:** its own isolated setup in the MEM schema by default: MEM.TESTBED_MEMORIES (VECTOR column), MEM.TESTBED_META, an IVF (or HNSW) vector index, and a TESTBED row in MEM.AGENT_PROFILES. Never touches the other agents' MEM tables; refuses SVN/ADMIN and another agent's profile id. Search uses VECTOR_DISTANCE with FETCH APPROX. Embeds outside the database or inside it (ONNX model via VECTOR_EMBEDDING; `memory load-onnx` uses DBMS_VECTOR). python-oracledb thin mode; login from NIMLAB_ORACLE_* env vars or ~/.config/nimlab/oracle_mem.json (`memory creds init`, mode 600), never stored in config or printed.
- **Embedding connections:** Embedding role, NVIDIA hosted NIMs (existing key), any OpenAI-compatible /v1/embeddings URL, Ollama, sentence-transformers in-process, in-database ONNX.
- **Automatic behaviour settings:** auto store/recall, what qualifies (all / salient / facts), de-duplication (off / exact / semantic), k, threshold, retention days, max records. Unreachable backend: warns once, answers without memory, retries later.

## v3.5.0
- **NVCF gRPC transport.** Models the scan marked `[NVCF gRPC ONLY]` (Canary, Parakeet, Conformer, Whisper ASR; Magpie zero-shot and Chatterbox TTS; Riva/Megatron translation) now run over `grpc.nvcf.nvidia.com:443` with NVIDIA's `nvidia-riva-client` (`riva.client.Auth`, SSL, metadata `function-id` + `authorization: Bearer <key>`). New module `nimlab/nvcf_grpc.py`.
- **Function IDs are data.** Stored per model in `data/endpoints.json` (`grpc_functions`, through `store.py`), taken from each model's NGC endpoint spec (what build.nvidia.com's "Try API" sample is built from), never hardcoded. The 200 sweep stores them; `./start.sh grpc refresh [model]` fetches them again (a pasted ID is kept unless `--force`); `grpc set <model> <id>` pastes one; a role with no ID fetches it once by itself. Stale-ID errors (NOT_FOUND / PERMISSION_DENIED) say to refresh.
- **ASR** via `ASRService.offline_recognize` or streaming (0.1 s chunks), whichever the model's sample uses, retrying the other mode if one is refused. Any input is converted to 16 kHz mono 16-bit WAV (pure Python for WAV, ffmpeg for other formats). `language_code` per role, per model (`grpc lang <model> es-US`) or per request.
- **TTS** via `SpeechSynthesisService.synthesize`, including the v3.2.0 cloned voice as the zero-shot audio prompt (+ transcript) on Magpie zero-shot.
- **Automatic routing:** the ASR, TTS and translate roles go over gRPC whenever their model is gRPC-only, so the single `testbed` endpoint, the call page and the terminal call use them unchanged. `transport: http|grpc` in a role overrides.
- **Scan:** gRPC models are reported as `USABLE via NVCF gRPC (ASR/TTS/NMT, function ...)` instead of just flagged, appear in the role pickers, and the sweep summary counts them. Maxine-style models with their own protos are listed but not driven.
- **Menus:** testbed option 10, launcher **G** (gRPC models) and **I** (install dependencies: `requirements.txt`, `pkg install python-grpcio ffmpeg` on Termux). Playground ASR/TTS tests on gRPC models go over gRPC.
- 45 new offline tests in `tests/test_grpc.py` with a fake riva module.

## v3.4.1
- **Thinking no longer leaks into replies.** Streaming passed reasoning models' `reasoning_content` through as reply text, so UIs on the test server showed the model's internal thinking (the terminal testbed didn't stream, so it looked fine). Now streamed and non-streamed replies drop `reasoning_content` / `reasoning`, strip `<think>` / `<thinking>` / `<reasoning>` blocks (including tags split across chunks and DeepSeek-style closing-tag-only output) and leaked gpt-oss `analysis...assistantfinal` text. If a model spends its whole token budget thinking, the reply says so instead of showing the thinking. Only `nimlab/api.py` changed. 359 tests pass (9 new in `tests/test_thinking.py`).

## v3.4.0
- **One model, one endpoint, one entity.** The server exposes a single model (`testbed`, rename with `serve settings model <name>`) at `POST /v1/chat/completions` that runs the whole 16-role stack. `/v1/models` lists only that model; per-role names are an off-by-default debug option (`serve settings roles all`). `testbed-agent` and the separate audio/image/embedding routes still work.
- **The persona always speaks.** Every reply is written by the Conversational Persona LLM from soul.md + the persona prompt. All other roles (including reasoning and coding) are abilities: they run with their own role prompt only and hand results to the persona, which keeps code, numbers and exact text intact. A client's system message is added after soul.md + persona prompt (`serve settings system ignore` drops it).
- **Multimodal input in chat messages:** images (vision / OCR / chart parser), audio (ASR, or omni audio for music and sound), video, PDFs (text layer, OCR for scans), Office, text, code, JSON and CSV files (up to 20,000 characters). Generation asks run image gen, audio gen or TTS; media is hosted at `/v1/files/<id>`. Audio output modality returns base64 speech in the cloned voice. Real token streaming from the persona model. `/v1/responses` for text, images and files (no streaming). Missing roles get a note naming the role to set. Roles that ran appear in `testbed_trace` and the server log.
- **Memory across requests:** each turn is stored once even though UIs resend the full chat; regenerations don't duplicate it.
- **Voice call test:** terminal call mode (testbed option 9 or `/call`): Enter to talk, mic -> ASR -> persona -> TTS (cloned voice) -> speaker, with per-step timing and barge-in; needs Termux:API and ffmpeg. Browser call page at `/call?t=<token>` (printed by `serve info`): hands-free or hold-to-talk, spoken replies, barge-in, attachments, timing per reply; plain HTML/JS, no outside downloads.
- **Attachments in testbed chat:** `/attach` (picker of recent files in Download, Documents, Pictures, Recordings), `/attach <paths>` (several per message), `/attached`, `/detach`; pasting a path still works.
- **Self-test** asks "who are you" and checks the answer against soul.md, and sends a mixed text + image + audio message and an image request through the one model.
- 350 offline tests pass (54 new in `tests/test_entity.py`).

## v3.3.0
- **OpenAI-compatible test server** (`nimlab/server.py`, stdlib only). Start it with `./start.sh serve`, launcher option O, or testbed option 8 (runs in the background while the testbed is open). It shows a copy-ready base URL (`http://127.0.0.1:PORT/v1`, plus the phone's Wi-Fi address when LAN access is on), a generated `sk-testbed-...` key (stored owner-only in `data/server_settings.json`, regenerate any time, never the NVIDIA key) and the model names.
- **Model names:** `testbed-agent` runs the full orchestrator (router, roles, memory with reranker, guardrail, tools); `testbed-<role>` for each set role calls that role's model endpoint or MCP tool; verified 200 OK chat/embedding/rerank models can be passed straight through. Which ones are exposed is configurable.
- **Routes:** `/v1/models`, `/v1/chat/completions` (non-streaming and SSE streaming with `[DONE]`, image/audio/video parts), `/v1/embeddings`, `/v1/rerank`, `/v1/audio/speech` (TTS role, cloned voice included), `/v1/audio/transcriptions` (ASR), `/v1/images/generations`. Bearer key check, CORS and OPTIONS, OpenAI-style error JSON.
- **Settings** (port, LAN bind, key, exposed models, logging, CORS, agent tool-call policy) created on first use; `./start.sh serve settings <name> <value>`.
- **Request log** with latency per call (`data/server_requests.jsonl`, `./start.sh serve log`); keys are masked.
- **UI configs** for Open WebUI, SillyTavern, LibreChat, Chatbox, one-line JSON (QR-friendly), curl and Python: `./start.sh serve ui`.
- **Public tunnel** via cloudflared when installed (`pkg install cloudflared`), with a quota warning; the key stays required.
- **Self-test:** `./start.sh serve test` calls the server like an external client (models, wrong key, CORS, chat, streamed chat, embeddings) and shows pass/fail.
- 294 offline tests pass (40 new in `tests/test_server.py`, against a real local server with fake NVIDIA and MCP backends). Not yet run against the live NVIDIA API or on the phone.

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
