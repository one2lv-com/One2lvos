/**
 * install_sovereign_core.js
 * Registers sovereign-agentic-core into One2lvOS and starts the FastAPI server.
 *
 * Run: node install_sovereign_core.js
 */

const { execFile, spawn } = require("child_process");
const path = require("path");
const http = require("http");
const fs = require("fs");

const SAC_ROOT = path.resolve(__dirname, "../../sovereign-agentic-core");
const SAC_PORT = 3003;   // 3002 is taken by One2lvOS core_service

// ---- load Registry (best-effort) ----
let Registry = null;
try {
  Registry = require("./reactor/registry.js");
} catch (e) {
  console.warn("[sac] Registry unavailable:", e.message);
}

function reg(key, value, meta) {
  if (Registry && typeof Registry.set === "function") {
    Registry.set(key, value, meta);
  } else {
    globalThis.__registry = globalThis.__registry || {};
    globalThis.__registry[key] = { value, meta };
  }
  console.log(`[sac] registered: ${key}`);
}

function waitForHttp(url, retries = 20, delayMs = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    function attempt() {
      http.get(url, (res) => {
        if (res.statusCode < 500) resolve(res.statusCode);
        else schedule();
      }).on("error", schedule);
    }
    function schedule() {
      attempts++;
      if (attempts >= retries) return reject(new Error(`${url} not reachable after ${retries} tries`));
      setTimeout(attempt, delayMs);
    }
    attempt();
  });
}

async function install() {
  console.log("\n[sac] Installing sovereign-agentic-core into One2lvOS...\n");

  // ── Start the FastAPI server ─────────────────────────────────────────── //
  const logFile = fs.openSync("/tmp/sovereign-agentic-core.log", "w");
  const proc = spawn(
    "python3", ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", String(SAC_PORT)],
    {
      cwd: SAC_ROOT,
      detached: true,
      stdio: ["ignore", logFile, logFile],
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    }
  );
  proc.unref();
  console.log(`[sac] FastAPI server starting on port ${SAC_PORT} (PID ${proc.pid})`);

  // ── Wait for it to come up ───────────────────────────────────────────── //
  try {
    const status = await waitForHttp(`http://localhost:${SAC_PORT}/api/status`, 30, 500);
    console.log(`[sac] Server online — HTTP ${status}`);
  } catch (e) {
    console.warn("[sac] Server may still be starting:", e.message);
  }

  // ── Register in One2lvOS ─────────────────────────────────────────────── //
  reg("sac.url",           `http://localhost:${SAC_PORT}`,            { type: "service_url",    source: "sovereign-agentic-core" });
  reg("sac.api.status",    `http://localhost:${SAC_PORT}/api/status`, { type: "endpoint",       source: "sovereign-agentic-core" });
  reg("sac.api.sessions",  `http://localhost:${SAC_PORT}/api/sessions`,{ type: "endpoint",      source: "sovereign-agentic-core" });
  reg("sac.ws",            `ws://localhost:${SAC_PORT}/ws`,           { type: "websocket",      source: "sovereign-agentic-core" });
  reg("sac.pid",           proc.pid,                                  { type: "process_id",     source: "sovereign-agentic-core" });
  reg("sac.manifest", {
    name: "Sovereign Agentic Core",
    components: ["LumenisReactor", "FluxCompass (SQLite)", "ITT Council of Seven", "VanguardNodePool"],
    council: ["Sentinel", "Navigator", "Witness", "Weaver", "Forge", "Oracle", "Architect"],
    port: SAC_PORT,
    root: SAC_ROOT,
    installed_at: new Date().toISOString(),
  }, { type: "service_manifest", source: "sovereign-agentic-core" });

  console.log(`\n[sac] ✓ Installation complete
  UI  : http://localhost:${SAC_PORT}
  API : http://localhost:${SAC_PORT}/api/status
  WS  : ws://localhost:${SAC_PORT}/ws
`);
}

if (require.main === module) {
  install().then(() => process.exit(0)).catch((e) => { console.error(e); process.exit(1); });
} else {
  module.exports = { install };
}
