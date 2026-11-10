"""Offline tests for lumenis_reactor_core.tool_engine (no network; temp data dir)."""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP = tempfile.mkdtemp(prefix="engine_test_")
os.environ["TOOL_ENGINE_DIR"] = TMP

from lumenis_reactor_core import tool_engine as te  # noqa: E402
from lumenis_reactor_core import sfcompute_mcp as sfc  # noqa: E402

CATALOG_SRC = Path(os.environ.get("ENGINE_TEST_CATALOG", "/tmp/sfc_tools_full.json"))
results = []


def check(name, cond, info=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info and not cond else ""))


class FakeMCP:
    calls = []

    async def list_tools(self):
        return json.loads(CATALOG_SRC.read_text())

    async def call_tool(self, name, args):
        FakeMCP.calls.append((name, args))
        return {"content": [{"type": "text", "text": json.dumps({"fake": name, "args": args})}]}


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def fake_session(c):
    return FakeMCP(), {"serverInfo": {"name": "fake"}, "protocolVersion": "test"}


sfc._client = lambda: FakeClient()
sfc._session = fake_session
facts = []
te.set_fact_sink(lambda k, v: facts.append((k, v)))


async def run():
    d = te.dispatch
    r = await d("sfcompute.list_nodes", {})
    check("call before learn -> 404", not r["ok"] and r["status"] == 404, r)

    r = await d("engine.learn")
    n = len(json.loads(CATALOG_SRC.read_text()))
    check("learn stores catalog", r["ok"] and r["result"]["learned"] == n and te.CATALOG_FILE.exists(), r)
    check("learn writes Compass fact", facts and facts[-1][0] == "tool_engine.catalog", facts)
    k = r["result"]["kinds"]
    check("kinds add up", k["remote_read"] + k["remote_write"] == n, k)
    r2 = await d("engine.learn")
    check("second identical learn -> unchanged, one version", r2["ok"] and not r2["result"]["changed"]
          and len(te.catalog_versions()) == 1, r2)

    r = await d("engine.describe", {"name": "list_nodes"})
    check("describe list_nodes from disk", r["ok"] and r["result"]["level"] == "remote_read"
          and "inputSchema" in r["result"], r)
    r = await d("engine.describe", {"name": "create_node"})
    check("describe create_node -> refused level", r["ok"] and r["result"]["level"] == "remote_write", r)

    FakeMCP.calls.clear()
    r = await d("sfcompute.create_node", {})
    check("create_node refused 403, nothing sent", not r["ok"] and r["status"] == 403 and not FakeMCP.calls, r)
    r = await d("sfcompute.buy_credits", {})
    check("buy_credits refused 403", not r["ok"] and r["status"] == 403, r)
    r = await d("sfcompute.list_secrets", {})
    check("list_secrets refused 403", not r["ok"] and r["status"] == 403, r)
    r = await d("sfcompute.open_mission", {})
    check("remote open_mission refused, points to local", not r["ok"] and "local.open_mission" in r["error"], r)

    r = await d("sfcompute.list_nodes", {})
    check("list_nodes goes remote", r["ok"] and r["source"] == "remote" and len(FakeMCP.calls) == 1, r)
    r = await d("sfcompute.list_nodes", {})
    check("second call served from cache", r["ok"] and r["source"] == "cache" and len(FakeMCP.calls) == 1, r)
    r = await d("sfcompute.list_nodes", {}, fresh=True)
    check("fresh=true skips cache", r["ok"] and r["source"] == "remote" and len(FakeMCP.calls) == 2, r)

    # schema check on a remote tool that has required args
    tm = te._tool_map()
    req_tool = next((nm for nm, t in tm.items() if te.remote_level(nm, t) == "remote_read"
                     and (t.get("inputSchema") or {}).get("required")), None)
    if req_tool:
        before = len(FakeMCP.calls)
        r = await d(f"sfcompute.{req_tool}", {})
        check(f"missing required arg on {req_tool} -> 422, nothing sent",
              not r["ok"] and r["status"] == 422 and len(FakeMCP.calls) == before, r)

    # local mission ledger
    r = await d("local.open_mission", {"title": "Test mission", "goal": "prove the engine", "tags": ["t"]})
    check("open_mission", r["ok"] and r["source"] == "local", r)
    mid = r["result"]["mission_id"]
    r = await d("local.post_update", {"mission_id": mid, "text": "first update"})
    check("post_update", r["ok"] and r["result"]["updates"] == 1, r)
    r = await d("local.save_chart", {"mission_id": mid, "name": "loss", "points": [[0, 1.0], [1, 0.5]]})
    check("save_chart", r["ok"], r)
    r = await d("local.get_mission", {"mission_id": mid})
    check("get_mission has update + chart", r["ok"] and len(r["result"]["updates"]) == 1
          and r["result"]["charts"][0]["name"] == "loss", r)
    r = await d("local.delete_chart", {"mission_id": mid, "name": "loss"})
    check("delete_chart", r["ok"], r)
    r = await d("local.finish_mission", {"mission_id": mid, "result": {"passed": True}, "verdict": "done"})
    check("finish_mission", r["ok"], r)
    r = await d("local.post_update", {"mission_id": mid, "text": "late"})
    check("no updates to finished mission", not r["ok"] and r["status"] == 400, r)
    r = await d("local.list_missions", {"status": "finished"})
    check("list_missions finished", r["ok"] and r["result"]["count"] == 1, r)
    r = await d("local.open_mission", {})
    check("local schema check: missing title -> 422", not r["ok"] and r["status"] == 422, r)
    r = await d("local.open_mission", {"title": "x", "bogus": 1})
    check("local schema check: unknown arg -> 422", not r["ok"] and r["status"] == 422, r)

    # artifacts: allowed folder vs refused paths
    logs = te.ROOT / "logs"
    logs.mkdir(exist_ok=True)
    probe = logs / "engine_test_probe.log"
    probe.write_text("line one\napi_key=sk-abcdefghijklmnopqrstuvwxyz123456\nline three\n")
    try:
        r = await d("local.export_file", {"path": "logs/engine_test_probe.log"})
        check("export_file from logs/", r["ok"] and r["result"]["size"] == probe.stat().st_size, r)
        aid = r["result"]["artifact_id"] if r["ok"] else ""
        r = await d("local.get_artifact", {"artifact_id": aid})
        check("get_artifact present", r["ok"] and r["result"]["present"], r)
        r = await d("local.export_file", {"path": ".env"})
        check("export .env refused", not r["ok"] and r["status"] == 403, r)
        r = await d("local.export_file", {"path": "logs/../lumenis-main.py"})
        check("path escape refused", not r["ok"] and r["status"] == 403, r)
        r = await d("local.export_file", {"path": "/etc/passwd"})
        check("/etc/passwd refused", not r["ok"] and r["status"] == 403, r)
        r = await d("local.query_logs", {"file": "engine_test_probe.log"})
        check("query_logs scrubs keys", r["ok"] and not any("sk-abc" in ln for ln in r["result"]["lines"])
              and any("[redacted]" in ln for ln in r["result"]["lines"]), r)
    finally:
        probe.unlink(missing_ok=True)

    r = await d("local.query_metrics", {})
    check("query_metrics", r["ok"] and "cpu_percent" in r["result"] and "services" in r["result"], r)

    # traces / audit, secret args redacted in the trace
    r = await d("sfcompute.create_node", {"api_key": "supersecretvalue"})
    tid = r["trace_id"]
    r = await d("local.get_trace", {"trace_id": tid})
    check("trace records refusal, secret arg redacted", r["ok"] and not r["result"]["ok"]
          and "supersecretvalue" not in json.dumps(r["result"]), r)
    r = await d("local.list_audit_events", {})
    check("audit lists refusals and writes", r["ok"] and r["result"]["count"] >= 5, r)
    r = await d("local.search_traces", {"tool": "list_nodes"})
    check("search_traces", r["ok"] and r["result"]["count"] >= 3, r)

    # rate limiter
    te._remote_calls.clear()
    old = te.RATE_PER_MIN
    te.RATE_PER_MIN = 2
    try:
        a = await d("sfcompute.list_nodes", {}, fresh=True)
        b = await d("sfcompute.list_nodes", {}, fresh=True)
        c = await d("sfcompute.list_nodes", {}, fresh=True)
        check("rate limit -> 429 on third", a["ok"] and b["ok"] and not c["ok"] and c["status"] == 429
              and c.get("retry_after_s") is not None, c)
    finally:
        te.RATE_PER_MIN = old
        te._remote_calls.clear()

    # catalog rollback: write a changed catalog version, then roll back
    data = json.loads(te.CATALOG_FILE.read_text())
    first_sha = data["sha256"]
    data["tools"] = data["tools"][:-1]
    FakeMCP_list = data["tools"]

    async def smaller():
        return FakeMCP_list
    FakeMCP.list_tools = lambda self: smaller()
    import time as _t
    _t.sleep(1.1)
    r = await d("engine.learn")
    check("changed catalog -> new version + diff", r["ok"] and r["result"]["changed"]
          and len(r["result"]["diff"]["removed"]) == 1 and len(te.catalog_versions()) == 2, r)
    r = await d("engine.rollback_catalog")
    check("rollback puts earlier catalog back", r["ok"] and te.load_catalog()["sha256"] == first_sha, r)

    r = await d("nope.thing")
    check("unknown namespace -> 404", not r["ok"] and r["status"] == 404, r)
    r = await d("engine.list", {"kind": "local"})
    check("engine.list local", r["ok"] and r["result"]["count"] == len(te.LOCAL_TOOLS), r)
    s = te.status()
    check("status reports no shell + permissions", s["shell"].startswith("none") and s["catalog_learned"], s)


asyncio.run(run())
passed = sum(1 for _, ok in results if ok)
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
