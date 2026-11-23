"""Commands & troubleshooting (3.7.4).

One source for the command cheat sheet: the launcher's "Commands &
troubleshooting" menu, `nimlab commands [area]`, `nimlab troubleshoot
[symptom]` and the README's Command reference all come from CATALOG and
SYMPTOMS below. tests/test_v374_commands.py checks CATALOG against the
argparse definitions (every subcommand and action is listed, and every
listed command parses), and that the README section matches render_markdown().

Flags on an entry: c = asks before running (stops, deletes or changes
something), l = sends real requests on your key, i = interactive or runs
until stopped. Arguments in <angle brackets> are asked for; [optional] ones
may be left empty.
"""

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

GROUPS = [
    ("setup", "Setup"),
    ("keys", "Keys"),
    ("models", "Models (discover, sweep, gRPC, roles, fleet)"),
    ("server", "Server and tunnel"),
    ("service", "Background service"),
    ("telegram", "Telegram"),
    ("mcp", "MCP"),
    ("memory", "Memory"),
    ("bench", "Benchmarks"),
    ("tests", "Tests"),
    ("scheduler", "Scheduler and heartbeat"),
    ("bugs", "Bugs and doctor"),
    ("selfadmin", "Self-admin"),
    ("other", "Other"),
]
GROUP_KEYS = [k for k, _ in GROUPS]

# (group, command, description, flags)
CATALOG = [
    # -- setup
    ("setup", "setup", "Run the guided setup from the first step", "i"),
    ("setup", "setup list", "Show every setup step and where it stands", ""),
    ("setup", "setup <step>", "Run one setup step (key, discover, functions, sweep, mcp, roles, grpc, memory, "
     "server, telegram, selfadmin, deps, shortcut, tunnel, service)", "i"),
    ("setup", "shortcut install", "Install the `nimlab` shortcut command", ""),
    ("setup", "shortcut status", "Show whether the shortcut is installed and where", ""),
    ("setup", "shortcut remove", "Remove the `nimlab` shortcut", "c"),
    ("setup", "platform", "Show this machine: OS, Python, venv, ffmpeg, cloudflared, RAM and swap, with hints", ""),
    # -- keys
    ("keys", "status <key|live|inventory|memory|catalog|discovered|endpoints|roles|color>", "One status field: key, live, inventory, memory, catalog, discovered, endpoints, "
     "roles, color", ""),
    ("keys", "persist-key", "Save the NVIDIA key so new shells and the service find it", "c"),
    ("keys", "forget-key", "Remove the saved NVIDIA key", "c"),
    ("keys", "mcp set-key", "Enter the MCP API key (hidden) and save it outside the project", "i"),
    ("keys", "mcp key-source", "Show where the MCP key comes from (env, saved or session)", ""),
    ("keys", "mcp delete-key", "Delete the saved MCP key", "c"),
    ("keys", "serve regen-key", "Make a new API key for the local server (clients need the new one)", "c"),
    ("keys", "selfadmin admin-key", "Make or show the self-admin key", "c"),
    # -- models
    ("models", "endpoints", "Custom endpoints and their models", ""),
    ("models", "endpoints add <name> <url>", "Add your own OpenAI-compatible gateway (asks for the key)", ""),
    ("models", "endpoints import <name>", "Add the models a custom endpoint lists", ""),
    ("models", "endpoints model <name> <model> [--kind <kind>]", "Add a model to a custom endpoint by hand", ""),
    ("models", "ui endpoints", "The Custom endpoints menu", "i"),
    ("models", "discover", "Find the models your key can see (uses the saved catalog when fresh)", "l"),
    ("models", "discover --refresh", "Discover again from NVIDIA, ignoring the saved catalog", "l"),
    ("models", "sweep", "The 200 OK test: one small request per model, writes the verified fleet", "l"),
    ("models", "sweep --plan-only", "Show what the 200 OK test would send, without sending it", ""),
    ("models", "roles", "Show which model plays each role", ""),
    ("models", "roles show", "Same as roles", ""),
    ("models", "roles candidates <role>", "List the models that can play one role", ""),
    ("models", "roles migrate", "Rewrite old role settings into the current form", "c"),
    ("models", "fleet", "Show the verified fleet from the last 200 OK test", ""),
    ("models", "grpc list", "List gRPC-only models and their function IDs", ""),
    ("models", "grpc menu", "The gRPC menu", "i"),
    ("models", "grpc check", "Check every gRPC function ID with a real call", "l"),
    ("models", "grpc asr", "Transcribe a short clip through the ASR function", "l"),
    ("models", "grpc tts", "Speak a line through the TTS function", "l"),
    ("models", "grpc fill", "Look up missing function IDs from the model pages", ""),
    ("models", "grpc refresh", "Read every model page again for function IDs", ""),
    ("models", "grpc set <model> <function-id>", "Set one model's function ID by hand", "c"),
    ("models", "grpc clear <model>", "Forget one model's function ID", "c"),
    ("models", "grpc lang <model> <language>", "Set the language code for a speech model", "c"),
    ("models", "grpc mode [<mode>]", "Show or set how gRPC models are called", ""),
    ("models", "tts", "Speak a test line with the TTS role", "l"),
    ("server", "audio devices", "Phones on the audio bus (nimbridge); * marks the active one", ""),
    ("server", "audio setup", "Register a phone step by step and print a ready-to-paste Termux block", ""),
    ("server", "audio add <name> [--label <label>]", "Register a phone for nimbridge and print its token once", ""),
    ("server", "audio add <name> --termux [--mic on|off] [--url <url>]",
     "Register a phone and print only its Termux block (for scripts)", ""),
    ("server", "audio remove <name>", "Forget a phone (its token stops working)", ""),
    ("server", "audio use <name>", "Make this phone the active one: audio and mic requests go to it only", ""),
    ("server", "audio release", "No active phone: nothing is relayed", ""),
    ("server", "audio tone [--target <name>]", "Play a short test tone on the active phone", ""),
    ("server", "audio say [<text>] [--target <name>]", "Speak text with the TTS role on the active phone", ""),
    ("models", "judge rank", "Rank candidate models for the roles with judge models", "l"),
    ("models", "judge entity", "Judge whole persona setups", "l"),
    ("models", "judge show", "Show the last judge results", ""),
    ("models", "judge apply", "Apply the judge's picks to the roles", "c"),
    # -- server
    ("server", "serve start", "Start the local OpenAI-style server in this terminal (Ctrl+C stops)", "i"),
    ("server", "serve start --tunnel", "Start the server with the public tunnel", "i"),
    ("server", "serve info", "Show the server address, model name and how to connect", ""),
    ("server", "serve test", "Self-test the running server through its one model name", "l"),
    ("server", "serve models", "List what the server's /v1/models returns", ""),
    ("server", "serve log", "Show the server's request log", ""),
    ("server", "serve ui", "Show the browser chat page address", ""),
    ("server", "serve settings", "Show or change server settings", ""),
    ("server", "serve menu", "The server menu", "i"),
    ("server", "serve", "Same as serve menu", "i"),
    ("server", "serve tunnel status", "Show the tunnel mode, whether it runs and its URL", ""),
    ("server", "serve tunnel quick", "Use a quick tunnel (random trycloudflare.com URL)", "c"),
    ("server", "serve tunnel named", "Use a named Cloudflare tunnel (asks for the token)", "i"),
    ("server", "serve tunnel off", "Turn the tunnel off (server stays local)", "c"),
    ("server", "serve tunnel auto <on|off>", "Start the tunnel together with the server, or not", "c"),
    ("server", "serve tunnel install", "Download cloudflared", ""),
    ("server", "serve tunnel token-delete", "Delete the saved tunnel token", "c"),
    ("server", "test tunnel", "Test the tunnel: /v1/models through the public URL with the server key", ""),
    # -- service
    ("service", "service status", "Is the service running, its children, restarts and stray copies", ""),
    ("service", "service brief", "One-line service state", ""),
    ("service", "service logs", "The service log (last lines)", ""),
    ("service", "service start", "Start the background service", ""),
    ("service", "service stop", "Stop the background service (server and bot stop too)", "c"),
    ("service", "service restart", "Restart the background service", "c"),
    ("service", "service install", "Install the service (runit on Termux, systemd on Linux)", "c"),
    ("service", "service remove", "Stop and remove the service files", "c"),
    ("service", "service cleanup", "Stop stray supervisor, server and bot copies", "c"),
    ("service", "update", "Clean restart after unzipping a release: stop, clean up, start once, health check", "c"),
    ("service", "update --stop", "Stop and clean up only (optional, before unzipping)", "c"),
    ("service", "ui service", "The Service & update menu", "i"),
    ("service", "service telegram <on|off>", "Run the Telegram bot inside the service, or not", "c"),
    ("service", "service scheduler <on|off>", "Run the job scheduler (heartbeat and jobs) inside the service, or not",
     "c"),
    ("service", "service boot", "Start the service when the device boots", "c"),
    ("service", "service run", "The supervisor itself (the service files run this; not for daily use)", "i"),
    # -- telegram
    ("telegram", "telegram status", "Bot name, mode, allowlist, owner and pollers", ""),
    ("telegram", "telegram test", "Check the bot token with Telegram (getMe)", ""),
    ("telegram", "telegram set-token", "Enter the bot token from @BotFather (hidden)", "i"),
    ("telegram", "telegram allow --capture", "Add yourself: send /start to the bot within 2 minutes", "i"),
    ("telegram", "telegram allow <telegram-id>", "Add a numeric Telegram ID to the allowlist", "c"),
    ("telegram", "telegram mode <polling|webhook>", "How the bot gets messages", "c"),
    ("telegram", "telegram voice <on|off>", "Answer voice notes with a voice note", "c"),
    ("telegram", "telegram refusal [<text>]", "Show or set the reply strangers get", ""),
    ("telegram", "telegram start", "Start the bot in the background (outside the service)", ""),
    ("telegram", "telegram stop", "Stop the background bot", "c"),
    ("telegram", "telegram run", "Run the bot in this terminal (Ctrl+C stops)", "i"),
    # -- mcp
    ("mcp", "mcp show", "MCP URL, key source and auth style", ""),
    ("mcp", "mcp test", "Connect to the MCP server and count its tools", ""),
    ("mcp", "mcp tools", "List every tool the MCP server offers", ""),
    ("mcp", "mcp set-url <url>", "Set the MCP server URL", "c"),
    ("mcp", "mcp auth <style>", "Set the auth style: x-api-key, bearer, header or none", "c"),
    ("mcp", "mcp menu", "The MCP menu", "i"),
    # -- memory
    ("memory", "memory show", "Memory settings and record counts", ""),
    ("memory", "memory status", "Backend, connection and queue in one screen", ""),
    ("memory", "memory test", "Connect, write, search and clean up a test memory", "l"),
    ("memory", "memory list", "The newest memories", ""),
    ("memory", "memory recall <query>", "Search memories the way a reply would (vector + keyword)", "l"),
    ("memory", "memory add <text>", "Save a memory now (Telegram /remember); pins \"my name is ...\"", "l"),
    ("memory", "memory identity", "Facts pinned about you (name, etc.): show, set <key> <value>, forget <key>", ""),
    ("memory", "memory set <setting> <value>", "Change one memory setting (e.g. auto_store on)", "c"),
    ("memory", "memory use <backend>", "Pick the backend: local, oracle, ords or auto", "c"),
    ("memory", "memory embed <provider> <model>", "Pick the embedding model", "c"),
    ("memory", "memory setup", "Guided memory setup", "i"),
    ("memory", "memory menu", "The memory menu", "i"),
    ("memory", "memory creds", "Enter the Oracle wallet login", "i"),
    ("memory", "memory ords show", "Show the ORDS connection (no secrets)", ""),
    ("memory", "memory ords login", "Enter the ORDS login (hidden)", "i"),
    ("memory", "memory pending", "Memories waiting for an embedding", ""),
    ("memory", "memory embed-pending", "Embed the waiting memories now", "l"),
    ("memory", "memory flush-queue", "Write queued memories to the backend now", ""),
    ("memory", "memory reembed", "Embed every memory again with the current model", "lc"),
    ("memory", "memory reembed --recreate", "Rebuild the vector column, then embed everything again", "lc"),
    ("memory", "memory forget <id>", "Delete one memory", "c"),
    ("memory", "memory prune", "Delete old, low-importance memories", "c"),
    ("memory", "memory sql <query>", "Run a read-only SQL query on the memory tables", ""),
    ("memory", "memory load-onnx", "Load the in-database ONNX embedding model", "c"),
    # -- bench
    ("bench", "bench router", "Router benchmark: routing accuracy and timings", "l"),
    ("bench", "bench router --compare", "Router benchmark with the router off for comparison", "l"),
    ("bench", "bench router --call", "Router benchmark on the voice-call path", "l"),
    ("bench", "bench router --show", "Show the last router benchmark", ""),
    # -- tests
    ("tests", "test", "List the tests, one per part of the lab", ""),
    ("tests", "test <name>", "Run one test (e.g. memory-recall, mcp, tunnel, telegram)", ""),
    ("tests", "test all", "Run every test and print a pass / fail table", "l"),
    ("tests", "test history", "The last test runs", ""),
    # -- scheduler (3.8.0)
    ("scheduler", "jobs list", "Every job: on/off, next run, last result", ""),
    ("scheduler", "jobs show <name>", "One job in full, with its recent runs", ""),
    ("scheduler", "jobs create <name> --schedule <spec> --do <action>",
     "Create a job (schedule: FREQ=MINUTELY;INTERVAL=30, a cron, or 'at YYYY-MM-DD HH:MM'; --type quill_prompt, "
     "nimlab_command, test, mcp_tool, shell or chain)", ""),
    ("scheduler", "jobs edit <name> --schedule <spec>", "Change a job (any --option of create)", ""),
    ("scheduler", "jobs run <name>", "Run a job once now", "l"),
    ("scheduler", "jobs enable <name>", "Turn a job on", ""),
    ("scheduler", "jobs disable <name>", "Turn a job off (its history stays)", ""),
    ("scheduler", "jobs delete <name>", "Delete a job", "c"),
    ("scheduler", "jobs history [name]", "Run history: status, time, bug IDs", ""),
    ("scheduler", "jobs next <name>", "The next run times", ""),
    ("scheduler", "jobs audit", "Every change to jobs and suggested actions, with who made it", ""),
    ("scheduler", "jobs tools", "The MCP tools the server offers now, to pick for a prompt task", ""),
    ("scheduler", "jobs free-time --tools a,b", "Ready-made hourly Free time job with the tools you pick", ""),
    ("scheduler", "heartbeat status", "Heartbeat on/off, next run, limits, the last report", ""),
    ("scheduler", "heartbeat run-now", "One heartbeat now: Quill decides and acts", "l"),
    ("scheduler", "heartbeat enable", "Turn the heartbeat on", ""),
    ("scheduler", "heartbeat disable", "Turn the heartbeat off", ""),
    ("scheduler", "heartbeat schedule <spec>", "How often the heartbeat runs", ""),
    ("scheduler", "heartbeat actions", "The suggested actions (list, show, add, edit, remove, enable, disable)", ""),
    ("scheduler", "heartbeat reports", "The last heartbeat reports: taken, skipped, why, where results went", ""),
    ("scheduler", "heartbeat set <max_actions|token_budget|time_budget_sec|escalate_failures_to> <value>",
     "Heartbeat limits", ""),
    ("scheduler", "scheduler status", "Is the scheduler running, and anything wrong with the jobs", ""),
    ("scheduler", "scheduler run", "Run the scheduler in this terminal (the service normally does)", ""),
    ("scheduler", "scheduler menu", "The Scheduler menu (old)", "i"),
    ("scheduler", "ui scheduler", "The Scheduler menu: on/off, add a job step by step, heartbeat", "i"),
    # -- bugs
    ("bugs", "doctor", "Check settings, keys, memory, MCP, platform and service for problems", ""),
    ("bugs", "doctor --no-mcp", "Doctor without contacting the MCP server", ""),
    ("bugs", "doctor --quick", "Quick doctor: no memory round trip, MCP or platform", ""),
    ("bugs", "doctor --json", "Doctor results as JSON (what Telegram /health reads)", ""),
    ("bugs", "doctor --fix", "Safe repairs: stale pid files, file modes, bad URLs; backs up first, checks again", "c"),
    ("bugs", "ui health", "The Health & repair menu", "i"),
    ("bugs", "bugs list", "Grouped error reports with bug IDs", ""),
    ("bugs", "bugs show <bug-id>", "One bug report in full (redacted)", ""),
    ("bugs", "bugs tail", "The newest bug log lines", ""),
    ("bugs", "bugs status", "Bug log size and retention", ""),
    ("bugs", "bugs prune", "Remove expired bug reports now", "c"),
    ("bugs", "bugs clear", "Delete every bug report", "c"),
    ("bugs", "report", "Write a support report (no secrets)", ""),
    ("bugs", "data overview", "What the data folder holds", ""),
    ("bugs", "data show <view>", "One data view (history, runs, ...)", ""),
    ("bugs", "data paths", "Where each data file lives", ""),
    ("bugs", "data migrate", "Move old data files into the current layout", "c"),
    # -- selfadmin
    ("selfadmin", "selfadmin status", "Self-admin on or off, shell access and the key", ""),
    ("selfadmin", "selfadmin on", "Let admins have the lab inspect and change its own setup", "c"),
    ("selfadmin", "selfadmin off", "Turn self-admin off", "c"),
    ("selfadmin", "selfadmin shell <on|off>", "Allow shell commands for self-admin, or not", "c"),
    ("selfadmin", "selfadmin others-read <on|off>", "Let non-admins read status, or not", "c"),
    ("selfadmin", "selfadmin fixes", "Fixes self-admin can apply", ""),
    ("selfadmin", "selfadmin audit", "What self-admin changed, newest first", ""),
    ("selfadmin", "selfadmin undo", "Undo the last self-admin change", "c"),
    # -- other
    ("other", "commands", "This list", ""),
    ("other", "commands <area>", "One group of this list (setup, keys, models, server, ...)", ""),
    ("other", "help", "Same as commands", ""),
    ("other", "troubleshoot", "Symptoms and what to run for each", ""),
    ("other", "troubleshoot <symptom>", "The steps for one symptom", ""),
    ("other", "colors", "Colour test and settings", ""),
    ("other", "colours", "Same as colors", ""),
]

FLAG_WORDS = {"c": "asks first", "l": "real requests", "i": "interactive"}

# Symptoms: (key, title, [(command, why)], note)
SYMPTOMS = [
    ("telegram-twice", "Telegram replies twice / duplicate bots",
     [("service status", "look for stray copies and for telegram listed twice"),
      ("service cleanup", "stop the stray copies"),
      ("telegram status", "pollers should be 1"),
      ("test telegram", "getMe, one poller, owner set")],
     "Another phone, PC or an old install polling the same bot also causes this: stop it there."),
    ("stray-copies", "\"Stray copies\" in service status",
     [("service status", "lists each stray with its pid"),
      ("service cleanup", "stops them"),
      ("service restart", "one clean supervisor"),
      ("test service", "running, children match the config, no strays")],
     "From 3.7.4 a second supervisor exits by itself; strays left by 3.7.3 need one cleanup."),
    ("port-busy", "The server won't start or the port is busy",
     [("service status", "the service may already run the server"),
      ("service cleanup", "stop stray serve copies"),
      ("serve info", "the port in use"),
      ("serve test", "self-test the server that runs")],
     "Change the port with: nimlab serve settings port <n>"),
    ("tunnel", "The tunnel isn't reachable",
     [("serve tunnel status", "mode, running or not, and the URL"),
      ("test tunnel", "200 = fine, 401 = key rejected, 530/1033/DNS = tunnel down or stale URL"),
      ("service restart", "a quick tunnel gets a new URL on restart"),
      ("serve tunnel install", "if cloudflared is missing")],
     "A quick tunnel's URL changes on every start; a named tunnel keeps its hostname."),
    ("mcp", "MCP 401/403 or no tools",
     [("mcp show", "URL, key source and auth style"),
      ("mcp test", "401/403 = key or auth style wrong; 0 tools = the admin console exposes none"),
      ("mcp auth <style>", "svn-dev.online/mcp-quill wants bearer"),
      ("mcp set-key", "enter the key again")],
     "Which tools appear is set in the MCP server's admin console."),
    ("memory", "Memory isn't recalling",
     [("memory status", "backend, connection and queue"),
      ("test memory-recall", "writes a marker, recalls it, cleans up"),
      ("memory recall <query>", "the same vector + keyword ranking a reply uses, with scores"),
      ("memory identity", "the name and other facts Quill always sees"),
      ("memory pending", "memories waiting for an embedding are not found by vector search"),
      ("memory embed-pending", "embed them now"),
      ("memory set auto_recall on", "recall before every reply")],
     ""),
    ("selftest", "A self-test check failed",
     [("bugs list", "the failed check's bug ID"),
      ("bugs show <bug-id>", "the full (redacted) error"),
      ("serve test", "run the server self-test again"),
      ("doctor", "settings that cause failures")],
     "A timeout on the image-and-audio check is usually a slow model, not a dead port."),
    ("grpc", "A gRPC model fails",
     [("grpc list", "every gRPC model needs a function ID"),
      ("grpc fill", "look up missing IDs"),
      ("grpc check", "a real call per ID"),
      ("setup deps", "nvidia-riva-client must be installed")],
     ""),
    ("after-update", "After an update",
     [("doctor", "settings and platform"),
      ("service cleanup", "old copies from the previous version"),
      ("setup list", "steps that need a rerun"),
      ("test all", "every part, with a pass / fail table")],
     "The MCP URL and auth style live in the project folder: after a fresh install enter them again."),
    ("scheduler", "A job or the heartbeat does not run",
     [("scheduler status", "is the scheduler running; broken jobs"),
      ("jobs list", "is the job on, and its next run"),
      ("jobs history", "SKIPPED, MISSED or FAILED runs, with bug IDs"),
      ("service scheduler on", "the service runs the scheduler"),
      ("test scheduler", "schedules parse and the scheduler runs")],
     "Times are in scheduler_settings.timezone (the system zone when empty)."),
    ("stop-all", "A full stop of everything",
     [("service telegram off", ""),
      ("telegram stop", ""),
      ("service stop", ""),
      ("service cleanup", "anything left over"),
      ("service status", "should show nothing running")],
     "On Termux with termux-services, run `sv down nimlab` first, or runit starts it again."),
]
SYMPTOM_KEYS = [k for k, *_ in SYMPTOMS]


# ---------------------------------------------------------------------------
# the catalog vs argparse
# ---------------------------------------------------------------------------
def _subparsers(parser):
    return next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))


def parser_commands(parser=None):
    """Every (subcommand, action) pair the CLI defines; action is None for a
    subcommand without an action list. -> list of strings like 'mcp test'."""
    if parser is None:
        from .cli import build_parser
        parser = build_parser()
    out = []
    for name, sp in _subparsers(parser).choices.items():
        acts = [a for a in sp._actions if not a.option_strings and a.dest == "action" and a.choices]
        if acts:
            out += [f"{name} {c}" for c in acts[0].choices]
        else:
            out.append(name)
    return out


def _words(cmd):
    return [w for w in cmd.split() if not w.startswith(("<", "[", "--"))]


def listed():
    """Command keys covered by the catalog: 'sub' and 'sub action'."""
    keys = set()
    for _g, cmd, _d, _f in CATALOG:
        w = _words(cmd)
        keys.add(w[0])
        if len(w) > 1:
            keys.add(f"{w[0]} {w[1]}")
    return keys


def missing(parser=None):
    """Subcommands / actions the CLI has that the catalog does not list."""
    have = listed()
    return [c for c in parser_commands(parser) if c not in have]


def sample_argv(cmd):
    """The command with sample values for its arguments, for parse checks."""
    out = []
    depth = 0
    for w in shlex.split(cmd):
        # skip a whole optional group: "[--kind <kind>]" is two words
        if depth or w.startswith("["):
            depth += w.count("[") - w.count("]")
            continue
        if w.startswith("<"):
            inner = w.strip("<>")
            out.append(inner.split("|")[0] if "|" in inner else "x")
        else:
            out.append(w)
    return out


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def group_title(key):
    return dict(GROUPS).get(key, key)


def entries(group=None):
    return [e for e in CATALOG if group is None or e[0] == group]


def find_group(word):
    w = (word or "").strip().lower()
    if not w:
        return None
    for k, title in GROUPS:
        if w == k or w == title.lower() or title.lower().startswith(w):
            return k
    aliases = {"key": "keys", "model": "models", "grpc": "models", "tunnel": "server", "serve": "server",
               "benchmarks": "bench", "benchmark": "bench", "test": "tests", "doctor": "bugs", "bug": "bugs",
               "self-admin": "selfadmin", "admin": "selfadmin", "mem": "memory", "tg": "telegram"}
    return aliases.get(w)


def flag_text(flags):
    return ", ".join(FLAG_WORDS[f] for f in flags if f in FLAG_WORDS)


def cheat_sheet(group=None, width=44):
    lines = []
    for key, title in GROUPS:
        if group and key != group:
            continue
        rows = entries(key)
        if not rows:
            continue
        lines.append(f"== {title} ==")
        for _g, cmd, desc, flags in rows:
            full = "nimlab " + cmd
            extra = f" ({flag_text(flags)})" if flags else ""
            if len(full) > width:
                lines.append(f"  {full}")
                lines.append(f"  {'':<{width}}  {desc}{extra}")
            else:
                lines.append(f"  {full:<{width}}  {desc}{extra}")
        lines.append("")
    return lines


def find_symptom(word):
    w = (word or "").strip().lower()
    for k, title, *_ in SYMPTOMS:
        if w == k or w in title.lower():
            return k
    return None


def symptom_lines(key=None):
    lines = []
    for n, (k, title, steps, note) in enumerate(SYMPTOMS, 1):
        if key and k != key:
            continue
        lines.append(f"{n}. {title}  [{k}]")
        for i, (cmd, why) in enumerate(steps, 1):
            lines.append(f"   {i}) nimlab {cmd}" + (f"  - {why}" if why else ""))
        if note:
            lines.append(f"   Note: {note}")
        lines.append("")
    return lines


README_BEGIN = "<!-- BEGIN COMMAND REFERENCE (generated by: nimlab commands --markdown) -->"
README_END = "<!-- END COMMAND REFERENCE -->"


def render_markdown():
    """The README's Command reference section body."""
    out = ["Every command, grouped. The launcher's main menu has the same list under **Commands & "
           "troubleshooting** (pick one to run it), and `nimlab commands [area]` prints it. "
           "*asks first* = stops, deletes or changes something; *real requests* = sends requests on your "
           "NVIDIA key; *interactive* = asks questions or runs until Ctrl+C.", ""]
    for key, title in GROUPS:
        rows = entries(key)
        if not rows:
            continue
        out.append(f"**{title}**")
        out.append("")
        for _g, cmd, desc, flags in rows:
            extra = f" *({flag_text(flags)})*" if flags else ""
            out.append(f"- `nimlab {cmd}`: {desc}{extra}")
        out.append("")
    from . import systests
    out.append("**The tests** (`nimlab test <name>`, or the Tests menu)")
    out.append("")
    for t in systests.TESTS:
        out.append(f"- `{t.name}`: {t.title}" + (" *(real requests)*" if t.live else ""))
    out.append("")
    out.append("**Troubleshooting** (`nimlab troubleshoot <symptom>`)")
    out.append("")
    for k, title, steps, note in SYMPTOMS:
        out.append(f"- {title} (`{k}`): " + ", then ".join(f"`nimlab {c}`" for c, _w in steps)
                   + (f". {note}" if note else ""))
    out.append("")
    return "\n".join(out)


def readme_section(text):
    """The generated block currently in a README text, or None."""
    if README_BEGIN not in text or README_END not in text:
        return None
    return text.split(README_BEGIN, 1)[1].split(README_END, 1)[0].strip("\n")


def update_readme(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    block = f"{README_BEGIN}\n{render_markdown()}\n{README_END}"
    if README_BEGIN in text and README_END in text:
        a = text.index(README_BEGIN)
        b = text.index(README_END) + len(README_END)
        new = text[:a] + block + text[b:]
    else:
        new = text.rstrip("\n") + "\n\n## Command reference\n\n" + block + "\n"
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return True
    return False


# ---------------------------------------------------------------------------
# the tunnel test
# ---------------------------------------------------------------------------
def public_url(srv=None, st=None):
    """The tunnel's public base URL, or ''."""
    from . import server as S, tunnel
    srv = S.load_settings() if srv is None else srv
    st = tunnel.read_status() if st is None else st
    t = tunnel.settings_of(srv)
    url = (st or {}).get("url") or ""
    if not url and t.get("mode") == "named" and (t.get("named") or {}).get("hostname"):
        url = "https://" + t["named"]["hostname"]
    return url.rstrip("/")


def _get(url, key, body=None, timeout=20):
    h = {"Authorization": f"Bearer {key}", "User-Agent": "nimlab-tunnel-test"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            txt = e.read(20000).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return e.code, txt


def tunnel_test(chat=False, http=None, srv=None, st=None):
    """GET <public URL>/v1/models with the server's own API key (read here,
    never printed). -> dict(ok, status, verdict, model, url, chat)."""
    from . import server as S
    srv = S.load_settings() if srv is None else srv
    url = public_url(srv, st)
    if not url:
        return {"ok": False, "status": None, "url": "", "model": None, "chat": None,
                "verdict": "No tunnel URL: the tunnel is off or has not started. Start it: nimlab serve tunnel "
                           "quick, then nimlab service restart (or nimlab serve start --tunnel)."}
    key = srv.get("api_key") or ""
    http = http or _get
    try:
        code, text = http(url + "/v1/models", key)
    except (urllib.error.URLError, socket.gaierror, socket.timeout, OSError) as e:
        reason = getattr(e, "reason", e)
        dns = isinstance(reason, socket.gaierror) or "Name or service not known" in str(reason) or \
            "nodename nor servname" in str(reason) or "getaddrinfo" in str(reason)
        return {"ok": False, "status": "DNS" if dns else "error", "url": url, "model": None, "chat": None,
                "verdict": ("DNS: the tunnel hostname does not resolve. The tunnel is down or the URL is stale "
                            "(a quick tunnel gets a new URL on every start).") if dns else
                f"Could not reach the tunnel: {type(e).__name__}: {str(reason)[:120]}"}
    model = None
    if code == 200:
        try:
            data = json.loads(text).get("data") or []
            model = data[0].get("id") if data else None
        except (ValueError, AttributeError, IndexError):
            model = None
        verdict = f"200: the tunnel reaches the server; model {model or '(none listed)'}."
    elif code == 401:
        verdict = ("401: the tunnel reached the server but it rejected the key. The server's key changed "
                   "(serve regen-key) or another server answers on this URL.")
    elif code == 530 or "1033" in (text or ""):
        verdict = (f"{code}{' / 1033' if '1033' in (text or '') else ''}: Cloudflare has no live tunnel behind "
                   "this URL. The tunnel is down or the URL is stale: nimlab serve tunnel status, then "
                   "nimlab service restart.")
    elif code in (502, 503, 504):
        verdict = f"{code}: the tunnel is up but the local server did not answer. Check: nimlab serve test"
    else:
        verdict = f"HTTP {code}: unexpected answer from the tunnel."
    res = {"ok": code == 200, "status": code, "url": url, "model": model, "verdict": verdict, "chat": None}
    if chat and code == 200:
        name = model or (srv.get("model_name") or "testbed")
        body = {"model": name, "max_tokens": 16, "stream": False,
                "messages": [{"role": "user", "content": "Reply with the single word: pong"}]}
        t0 = time.monotonic()
        try:
            c2, t2 = http(url + "/v1/chat/completions", key, body)
        except (urllib.error.URLError, OSError) as e:
            c2, t2 = None, str(e)
        ms = int((time.monotonic() - t0) * 1000)
        reply = ""
        if c2 == 200:
            try:
                reply = json.loads(t2)["choices"][0]["message"]["content"].strip()[:80]
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                reply = ""
        res["chat"] = {"ok": c2 == 200, "status": c2, "ms": ms, "reply": reply}
    return res


def tunnel_lines(res):
    out = [f"Tunnel URL : {res['url'] or '(none)'}", f"Result     : {res['verdict']}"]
    c = res.get("chat")
    if c:
        out.append(f"Chat test  : {'ok' if c['ok'] else 'failed'} (HTTP {c['status']}, {c['ms']} ms)"
                   + (f": {c['reply']!r}" if c.get("reply") else ""))
    return out


def tunnel_screen(res):
    """tunnel_lines in colour for the terminal (3.8.1): the verdict in green
    when the tunnel answers 200, red otherwise."""
    from . import colors as C, paint
    if not C.enabled():
        return tunnel_lines(res)
    out = []
    for ln in tunnel_lines(res):
        lab, _, val = ln.partition(" : ")
        if lab.startswith("Tunnel URL"):
            val = C.url(val) if res.get("url") else C.warn(val)
        elif lab.startswith("Result"):
            val = (C.ok if res.get("ok") else C.err)(val[:4]) + paint.cmds(val[4:])
        elif lab.startswith("Chat test"):
            c = res.get("chat") or {}
            val = (C.ok if c.get("ok") else C.err)(val.split(" ", 1)[0]) + " " + C.dim(val.split(" ", 1)[1])
        out.append(C.label(lab) + C.dim(" : ") + val)
    return out


# ---------------------------------------------------------------------------
# running from the menu
# ---------------------------------------------------------------------------
def fill_args(cmd, ask):
    """Ask for each <argument> ([optional] ones may be empty). -> argv or None."""
    argv = []
    for w in shlex.split(cmd):
        if w.startswith(("<", "[")):
            optional = w.startswith("[")
            inner = w.strip("[]<>")
            hint = f" ({inner.replace('|', ' or ')})" if "|" in inner else ""
            v = ask(f"{inner.split('|')[0] if '|' in inner else inner}{hint}{' (Enter to skip)' if optional else ''}: ")
            if v is None:
                return None
            v = v.strip()
            if not v:
                if optional:
                    continue
                return None
            # 3.8.2: one answer is one argument. Splitting it on spaces broke
            # `jobs create ... --do <action>` ("summarize my day" became three
            # arguments, so argparse refused the job). An argument named
            # "...s" (several) is still split.
            argv += shlex.split(v) if inner.endswith(("...", "args")) else [v]
        else:
            argv.append(w)
    return argv


def run_cli(argv, runner=None):
    """Run `nimlab <argv>` with the terminal attached. -> exit code."""
    if runner:
        return runner(argv)
    try:
        return subprocess.call([sys.executable, "-m", "nimlab"] + list(argv))
    except KeyboardInterrupt:
        return 130


def run_captured(argv, say, runner=None):
    """Run `nimlab <argv>`, showing its output as it comes and keeping it
    (to offer the next steps it names). -> (code, text)."""
    if runner:
        return runner(argv), ""
    lines = []
    env = dict(os.environ, NIMLAB_COLOR=os.environ.get("NIMLAB_COLOR", "1" if sys.stdout.isatty() else "0"))
    try:
        p = subprocess.Popen([sys.executable, "-m", "nimlab"] + list(argv), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        for ln in p.stdout:
            say(ln.rstrip("\n"))
            lines.append(ln)
        return p.wait(), "".join(lines)
    except KeyboardInterrupt:
        return 130, "".join(lines)


def run_entry(cmd, flags, ask, say, runner=None, capture=False):
    argv = fill_args(cmd, ask)
    if argv is None:
        say("Cancelled (an argument was empty).")
        return None
    if "c" in flags:
        a = ask(f"Run `nimlab {' '.join(argv)}`? It changes or stops something. [y/N]: ")
        if (a or "").strip().lower() not in ("y", "yes"):
            say("Not run.")
            return None
    from . import colors as C
    say(C.paint(f"$ nimlab {' '.join(shlex.quote(a) for a in argv)}", "accent", "bold"))
    if capture and "i" not in flags:
        code, text = run_captured(argv, say, runner)
        say((C.ok if code == 0 else C.err)(f"(exit code {code})"))
        return code, text
    code = run_cli(argv, runner)
    say((C.ok if code == 0 else C.err)(f"(exit code {code})"))
    return code


def _wrap(text, indent=6):
    """Wrap a description to the screen width (a phone in Termux)."""
    import textwrap
    from . import colors as C
    width = max(30, C.screen_width() - indent)
    return textwrap.wrap(text, width) or [""]


def _rule():
    from . import colors as C
    return C.rule(min(50, C.screen_width()))


def menu(ask=input, say=print, runner=None):
    """The launcher's Commands & troubleshooting screen."""
    from . import colors as C, paint

    def _ask(p):
        try:
            return ask(p)
        except EOFError:
            return None
    while True:
        say("")
        say(C.header("COMMANDS & TROUBLESHOOTING"))
        say(_rule())
        say(C.section("Commands by area"))
        for i, (k, title) in enumerate(GROUPS, 1):
            short = title.split(" (")[0]
            say(C.entry(i, short, f"{len(entries(k))} commands", pad=24))
        say(C.section("Help"))
        say(C.entry("t", "Troubleshooting", "by symptom", pad=24))
        say(C.entry("n", "Test the tunnel", "/v1/models, key hidden", pad=24))
        say(C.entry("s", "Tests menu", "one per part", pad=24))
        say(C.entry("w", "Scheduler", "jobs, heartbeat", pad=24))
        say(C.entry(0, "Back"))
        c = (_ask(paint.ask("\nSelection: ")) or "b").strip().lower()
        if c in ("b", "q", "0", ""):
            return 0
        if c == "t":
            symptoms_menu(_ask, say, runner)
        elif c == "n":
            tunnel_menu(_ask, say)
        elif c == "s":
            from . import systests
            systests.menu(_ask, say)
        elif c == "w":
            from . import jobscli
            jobscli.menu(_ask, say)
        elif c.isdigit() and 1 <= int(c) <= len(GROUPS):
            group_menu(GROUPS[int(c) - 1][0], _ask, say, runner)


def short_label(desc, width=44):
    """The first clause of a description, cut to one phone line (3.8.2)."""
    import re as _re
    t = _re.split(r"(?<=[a-z0-9)])[.;:](\s|$)| \(|, then | -- ", desc.strip(), maxsplit=1)[0].strip()
    return t if len(t) <= width else t[: width - 1].rstrip() + "…"


PAGE = 10


def group_menu(group, ask, say, runner=None):
    """3.8.2: one short line per command, ten to a page; `?` shows the full
    commands and descriptions. Picking one runs it, and the next steps its
    output names can be picked right after (no retyping)."""
    from . import colors as C, paint
    rows = entries(group)
    page, detail = 0, False
    while True:
        pages = max(1, (len(rows) + PAGE - 1) // PAGE)
        page = min(page, pages - 1)
        say("")
        say(C.header(group_title(group).upper()) + (C.dim(f"  page {page + 1}/{pages}") if pages > 1 else ""))
        say(_rule())
        start = page * PAGE
        for i, (_g, cmd, desc, flags) in enumerate(rows[start:start + PAGE], start + 1):
            mark = C.warn(" *") if "c" in flags else ""
            if detail:
                say(C.entry(i, "nimlab " + cmd) + mark)
                for ln in _wrap(desc):
                    say("      " + C.dim(ln))
            else:
                say(C.entry(i, short_label(desc)) + mark)
        say(C.dim("  * asks before it changes or stops something"))
        nav = (["n) next page"] if page < pages - 1 else []) + (["p) previous"] if page else []) + \
              ["?) " + ("short list" if detail else "show commands"), "0) back"]
        say(C.dim("  " + "   ".join(nav)))
        c = (ask(paint.ask("Run which? ")) or "b").strip().lower()
        if c in ("b", "q", "0", ""):
            return
        if c == "n" and page < pages - 1:
            page += 1
            continue
        if c == "p" and page:
            page -= 1
            continue
        if c == "?":
            detail = not detail
            continue
        if c.isdigit() and 1 <= int(c) <= len(rows):
            _g, cmd, _d, flags = rows[int(c) - 1]
            if cmd == "test tunnel":
                tunnel_menu(ask, say)
            else:
                follow(run_entry(cmd, flags, ask, say, runner, capture=True), ask, say, runner)
            ask(paint.ask("Press Enter to go back to the list "))


SUGGEST = __import__("re").compile(r"(?:^|[\s(`'\"])nimlab ([a-z][a-z0-9 _./=<>-]*[a-z0-9>])")


def suggestions(text, limit=6):
    """`nimlab <command>` next steps named in a command's output that are on
    the list, so the menu can offer them directly."""
    out = []
    for m in SUGGEST.finditer(text or ""):
        cmd = m.group(1).strip().rstrip(".")
        cmd = __import__("re").split(r"\s+(?:or|and|then|to|for|if|\()\s*", cmd)[0].strip()
        words = cmd.split()
        if not words or cmd in out:
            continue
        if any(_words(c)[: len(words[:2])] == words[:2] for _g, c, _d, _f in CATALOG):
            out.append(cmd)
        if len(out) >= limit:
            break
    return out


def follow(result, ask, say, runner=None):
    """Offer the next steps a command's output named (3.8.2: no dead ends)."""
    if not isinstance(result, tuple):
        return
    _code, text = result
    nxt = suggestions(text)
    while nxt:
        from . import colors as C, paint
        say("")
        say(C.header("NEXT STEPS"))
        for i, cmd in enumerate(nxt, 1):
            say(C.entry(i, cmd))
        say(C.entry(0, "Back"))
        c = (ask(paint.ask("Run which? ")) or "0").strip()
        if not c.isdigit() or not 1 <= int(c) <= len(nxt):
            return
        cmd = nxt.pop(int(c) - 1)
        result = run_entry(cmd, _flags_of(cmd), ask, say, runner, capture=True)
        if isinstance(result, tuple):
            nxt = suggestions(result[1]) or nxt


def _flags_of(cmd):
    words = _words(cmd)
    for _g, c, _d, f in CATALOG:
        if _words(c)[:2] == words[:2]:
            return f
    return ""


def symptoms_menu(ask, say, runner=None):
    from . import colors as C, paint
    while True:
        say("")
        say(C.header("TROUBLESHOOTING"))
        say(_rule())
        for i, (k, title, *_r) in enumerate(SYMPTOMS, 1):
            say(C.entry(i, title))
        say(C.entry(0, "Back"))
        c = (ask(paint.ask("\nWhich problem? ")) or "b").strip().lower()
        if c in ("b", "q", "0", ""):
            return
        if not (c.isdigit() and 1 <= int(c) <= len(SYMPTOMS)):
            continue
        k, title, steps, note = SYMPTOMS[int(c) - 1]
        while True:
            say("")
            say(C.header(title.upper()))
            say(_rule())
            for i, (cmd, why) in enumerate(steps, 1):
                say(C.entry(i, "nimlab " + cmd))
                if why:
                    for ln in _wrap(why):
                        say("      " + C.dim(ln))
            if note:
                for j, ln in enumerate(_wrap("Note: " + note, 2)):
                    say("  " + (C.hint(ln) if C.enabled() else ln))
            say(C.entry("a", "Run them all in order", "asks before each", pad=24))
            say(C.entry(0, "Back"))
            s = (ask(paint.ask("\nRun which? ")) or "b").strip().lower()
            if s in ("b", "q", "0", ""):
                break
            todo = list(range(len(steps))) if s == "a" else \
                ([int(s) - 1] if s.isdigit() and 1 <= int(s) <= len(steps) else [])
            for i in todo:
                cmd = steps[i][0]
                if s == "a":
                    a = ask(paint.ask(f"Next: nimlab {cmd}. Run it? [Y/n/q]: "))
                    a = (a or "").strip().lower()
                    if a == "q":
                        break
                    if a in ("n", "no"):
                        continue
                if cmd.startswith("test tunnel"):
                    tunnel_menu(ask, say)
                else:
                    run_entry(cmd, _flags_of(cmd), ask, say, runner)
            if todo:
                ask(paint.ask("Press Enter to go back "))


def tunnel_menu(ask, say, http=None):
    from . import colors as C
    say(C.dim("Testing the tunnel: GET <public URL>/v1/models with the server's key (the key is not shown)..."))
    res = tunnel_test(http=http)
    for ln in tunnel_screen(res):
        say(ln)
    if res["ok"]:
        from . import paint
        a = (ask(paint.ask("Also send one short chat turn through the tunnel (one real request)? [y/N]: ")) or "")
        if a.strip().lower() in ("y", "yes"):
            res = tunnel_test(chat=True, http=http)
            for ln in tunnel_screen(res)[2:]:
                say(ln)
    return res


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_commands(args):
    if getattr(args, "markdown", False):
        print(render_markdown())
        return 0
    if getattr(args, "menu", False):
        return menu()
    area = getattr(args, "area", None)
    group = None
    if area:
        group = find_group(area)
        if not group:
            print(f"No area '{area}'. Areas: {', '.join(GROUP_KEYS)}")
            return 2
    print("\n".join(sheet_screen(cheat_sheet(group))).rstrip())
    if not group:
        print("\nOne area: nimlab commands <area>. Problems: nimlab troubleshoot. Tests: nimlab test. "
              "In the launcher: main menu > Commands & troubleshooting.")
    return 0


def cmd_troubleshoot(args):
    s = getattr(args, "symptom", None)
    key = None
    if s:
        key = find_symptom(s)
        if not key:
            print(f"No symptom '{s}'. Symptoms: {', '.join(SYMPTOM_KEYS)}")
            return 2
    print("\n".join(symptom_screen(symptom_lines(key))).rstrip())
    return 0


def sheet_screen(lines):
    """cheat_sheet lines in colour for a terminal (3.8.1); plain otherwise."""
    from . import colors as C
    if not C.enabled():
        return lines
    out = []
    for ln in lines:
        if ln.startswith("== ") and ln.endswith(" =="):
            out.append(C.header(ln[3:-3].upper()))
            continue
        s = ln.strip()
        if s.startswith("nimlab "):
            lead = ln[:len(ln) - len(ln.lstrip())]
            parts = s.split("  ", 1)
            cmd = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            flags = ""
            if rest.endswith(")") and " (" in rest:
                rest, flags = rest.rsplit(" (", 1)
                flags = " (" + flags
            out.append(lead + C.paint(cmd, "accent", "bold") + ("  " + C.dim(rest) if rest else "")
                       + C.warn(flags))
        elif s:
            out.append(ln[:len(ln) - len(ln.lstrip())] + C.dim(s))
        else:
            out.append(ln)
    return out


def symptom_screen(lines):
    """symptom_lines in colour: titles as sections, steps as menu entries."""
    import re
    from . import colors as C, paint
    if not C.enabled():
        return lines
    out = []
    for ln in lines:
        m = re.match(r"^(\d+)\. (.*)  \[([a-z0-9-]+)\]$", ln)
        if m:
            out.append(C.paint(m.group(1) + ".", C.menu_rgb(int(m.group(1))), "bold") + " "
                       + C.section(m.group(2)) + "  " + C.dim("[" + m.group(3) + "]"))
            continue
        m = re.match(r"^(\s+)(\d+\))( nimlab .*?)(  - .*)?$", ln)
        if m:
            out.append(m.group(1) + C.paint(m.group(2), C.menu_rgb(int(m.group(2)[:-1])), "bold")
                       + C.paint(m.group(3), "accent") + C.dim(m.group(4) or ""))
            continue
        if ln.strip().startswith("Note:"):
            out.append(C.hint(ln))
            continue
        out.append(paint.cmds(ln))
    return out


def add_parsers(sub):
    for name in ("commands", "help"):
        p = sub.add_parser(name, help="Every nimlab command, grouped, with a one-line description"
                           if name == "commands" else "Same as commands")
        p.add_argument("area", nargs="?", help="one area: " + ", ".join(GROUP_KEYS))
        p.add_argument("--markdown", action="store_true", help="print the README section")
        p.add_argument("--menu", action="store_true", help="the interactive menu (the launcher uses this)")
        p.set_defaults(fn=cmd_commands)
    p = sub.add_parser("troubleshoot", help="Symptoms and what to run for each")
    p.add_argument("symptom", nargs="?", help="one of: " + ", ".join(SYMPTOM_KEYS))
    p.set_defaults(fn=cmd_troubleshoot)

