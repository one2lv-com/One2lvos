/**
 * arcade_register.js
 * Registers the AI Arcade MCP server into the One2lvOS Registry
 * so any JS component (UI, Council frontend, etc.) can discover it.
 *
 * Run once after startup:   node arcade_register.js
 */

// Support both CommonJS (Node) and browser globals
const isNode = typeof module !== "undefined" && module.exports;

async function registerArcade() {
  const ARCADE_URL = "http://localhost:8003";

  // ---- try to import the Registry module (Node context) ----
  let Registry;
  try {
    Registry = require("./reactor/registry.js");
  } catch (e) {
    console.warn("[arcade_register] Registry module not available:", e.message);
    Registry = null;
  }

  const entry = {
    name: "AI Arcade",
    description: "50+ games for AI agents, accessible via MCP protocol",
    url: ARCADE_URL,
    mcp_url: `${ARCADE_URL}/mcp`,
    sse_url: `${ARCADE_URL}/sse`,
    protocol: "MCP 2024-11-05",
    transport: ["Streamable HTTP (POST /mcp)", "HTTP+SSE (/sse + /messages)"],
    games: [
      "chess", "go", "checkers", "othello", "tictactoe", "connect4",
      "minesweeper", "sudoku", "scrabble", "battleship",
      "pacman", "tetris", "space_invaders", "pong", "universal_paperclips",
    ],
    library_size: 51,
    status: "online",
    registered_at: new Date().toISOString(),
  };

  if (Registry && typeof Registry.set === "function") {
    Registry.set("arcade.mcp.url",  entry.mcp_url,  { service: "AI Arcade", type: "mcp_endpoint" });
    Registry.set("arcade.sse.url",  entry.sse_url,  { service: "AI Arcade", type: "sse_endpoint" });
    Registry.set("arcade.info",     entry,           { service: "AI Arcade", type: "service_info" });
    console.log("[arcade_register] ✓ AI Arcade registered in One2lvOS Registry");
  } else {
    // Fallback: expose on globalThis so browser/other code can read it
    if (typeof globalThis !== "undefined") {
      globalThis.__arcade = entry;
    }
    console.log("[arcade_register] ✓ AI Arcade info available (Registry not loaded):", entry.mcp_url);
  }

  // ---- verify the arcade server is reachable ----
  try {
    const http = isNode ? require("http") : null;
    if (http) {
      await new Promise((resolve, reject) => {
        const req = http.get(`${ARCADE_URL}/`, (res) => {
          console.log(`[arcade_register] Arcade health: HTTP ${res.statusCode}`);
          resolve(res.statusCode);
        });
        req.on("error", reject);
        req.setTimeout(3000, () => { req.destroy(); reject(new Error("timeout")); });
      });
    }
  } catch (err) {
    console.warn("[arcade_register] Could not reach arcade server:", err.message);
  }

  return entry;
}

// Auto-run if executed directly
if (isNode && require.main === module) {
  registerArcade().then(() => process.exit(0)).catch((e) => {
    console.error(e); process.exit(1);
  });
} else {
  module.exports = { registerArcade };
}
