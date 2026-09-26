/**
 * install_minmax.js
 * Installs One2lvOS Phase 9 (minmax) modules into the running OS:
 *   - Registers DeltaEngine (∆⁹) in the Registry
 *   - Registers SystemDynamics (³) in the Registry
 *   - Bridges the minmax Council into One2lvOS
 *
 * Run: node install_minmax.js
 */

const path = require("path");
const MINMAX_ROOT = path.resolve(__dirname, "../../minmax/opt/one2lv");

// ---- load Registry (best-effort) ----
let Registry = null;
try {
  Registry = require("./reactor/registry.js");
} catch (e) {
  console.warn("[minmax] Registry unavailable:", e.message);
}

function reg(key, value, meta) {
  if (Registry && typeof Registry.set === "function") {
    Registry.set(key, value, meta);
  } else if (typeof globalThis !== "undefined") {
    globalThis.__registry = globalThis.__registry || {};
    globalThis.__registry[key] = { value, meta };
  }
  console.log(`[minmax] registered: ${key}`);
}

async function install() {
  console.log("\n[minmax] Installing One2lvOS Phase 9 (minmax) modules...\n");

  // ── Delta Engine ─────────────────────────────────────────────────────── //
  let DeltaEngine, DELTA_LAYERS;
  try {
    ({ DeltaEngine, DELTA_LAYERS } = await import(`${MINMAX_ROOT}/modules/delta_engine.js`));
    const engine = new DeltaEngine();
    // Prime with default 9 layers matching the Phase 9 spec
    const layerNames = [
      "perception", "reasoning", "planning",
      "execution", "reflection", "synthesis",
      "validation", "adaptation", "oracle",
    ];
    layerNames.forEach((name) => engine.addLayer(name, 1.0));

    reg("minmax.delta_engine.instance",  engine,       { type: "delta_engine",   source: "minmax" });
    reg("minmax.delta_engine.layers",    DELTA_LAYERS, { type: "constant",        source: "minmax" });
    reg("minmax.delta_engine.module",    `${MINMAX_ROOT}/modules/delta_engine.js`, { type: "module_path" });
    console.log(`[minmax] DeltaEngine ∆⁹ ready — ${engine.layers.length} layers`);
  } catch (e) {
    console.warn("[minmax] DeltaEngine load failed:", e.message);
  }

  // ── System Dynamics (3D Vectors) ─────────────────────────────────────── //
  try {
    const sd = await import(`${MINMAX_ROOT}/modules/system_dynamics.js`);
    reg("minmax.system_dynamics.module", `${MINMAX_ROOT}/modules/system_dynamics.js`, { type: "module_path" });
    reg("minmax.system_dynamics.createVector3D", sd.createVector3D ?? null, { type: "function", source: "minmax" });
    // Smoke-test: create a unit vector
    if (typeof sd.createVector3D === "function") {
      const v = sd.createVector3D(Math.PI / 4, Math.PI / 4, 1.0);
      console.log(`[minmax] SystemDynamics ³ ready — test vector: x=${v.x} y=${v.y} z=${v.z}`);
    }
  } catch (e) {
    console.warn("[minmax] SystemDynamics load failed:", e.message);
  }

  // ── Phase 9 Council ──────────────────────────────────────────────────── //
  reg("minmax.council.module",  `${MINMAX_ROOT}/ai/council/council.js`,  { type: "module_path", source: "minmax" });
  reg("minmax.council.planner", `${MINMAX_ROOT}/ai/council/planner.js`,  { type: "module_path", source: "minmax" });
  reg("minmax.council.engine",  `${MINMAX_ROOT}/ai/council/engine.js`,   { type: "module_path", source: "minmax" });

  // ── Service manifest ─────────────────────────────────────────────────── //
  reg("minmax.manifest", {
    name: "One2lvOS Phase 9 (minmax)",
    version: "4.0.0",
    root: MINMAX_ROOT,
    features: ["DeltaEngine ∆⁹", "SystemDynamics ³", "Phase9 Council", "VectorDB", "SecureRPC", "SandboxExecutor"],
    installed_at: new Date().toISOString(),
  }, { type: "service_manifest", source: "minmax" });

  console.log("\n[minmax] ✓ Installation complete\n");
}

if (require.main === module) {
  install().then(() => process.exit(0)).catch((e) => { console.error(e); process.exit(1); });
} else {
  module.exports = { install };
}
