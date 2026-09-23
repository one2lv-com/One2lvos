/**
 * install_all.js
 * Master installer — runs minmax + sovereign-agentic-core installs,
 * then registers everything (including AI Arcade) in One2lvOS.
 *
 * Run: node install_all.js
 */

const http = require("http");

async function checkHttp(url) {
  return new Promise((resolve) => {
    http.get(url, (res) => resolve(res.statusCode)).on("error", () => resolve(null));
  });
}

async function main() {
  console.log("╔══════════════════════════════════════════════════════╗");
  console.log("║    One2lvOS — Full Stack Installer                   ║");
  console.log("╚══════════════════════════════════════════════════════╝\n");

  // ── 1. minmax (Phase 9) ──────────────────────────────────────────────── //
  console.log("── Installing minmax (Phase 9 Delta Engine) ────────────");
  const { install: installMinmax } = require("./install_minmax.js");
  await installMinmax();

  // ── 2. sovereign-agentic-core ────────────────────────────────────────── //
  console.log("── Installing sovereign-agentic-core ───────────────────");
  const { install: installSAC } = require("./install_sovereign_core.js");
  await installSAC();

  // ── 3. AI Arcade ────────────────────────────────────────────────────────//
  console.log("── Registering AI Arcade MCP ───────────────────────────");
  const { registerArcade } = require("./arcade_register.js");
  await registerArcade();

  // ── 4. Summary ──────────────────────────────────────────────────────────//
  const services = [
    { name: "One2lvOS Core Service",     url: "http://localhost:3002/health" },
    { name: "One2lvOS UI",               url: "http://localhost:9000" },
    { name: "Lumenis Space Agent",        url: "http://localhost:9001" },
    { name: "AI Arcade MCP",             url: "http://localhost:8003" },
    { name: "Sovereign Agentic Core",    url: "http://localhost:3003/api/status" },
  ];

  console.log("\n╔══════════════════════════════════════════════════════╗");
  console.log("║    One2lvOS Service Status                           ║");
  console.log("╠══════════════════════════════════════════════════════╣");
  for (const svc of services) {
    const status = await checkHttp(svc.url);
    const symbol = status && status < 500 ? "✓" : "✗";
    const label  = (svc.name + " ").padEnd(34, "·");
    console.log(`║  ${symbol}  ${label} ${svc.url.replace("http://localhost", ":")}  ║`);
  }
  console.log("╚══════════════════════════════════════════════════════╝\n");
}

main().catch((e) => { console.error(e); process.exit(1); });
