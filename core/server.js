import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import http from "http";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { WebSocketServer } from "ws";

import { establishBootVector } from "./boot_vector.js";
import reactor from "../reactor_core/reactor.js";
import { lumenisBuild } from "../reactor_core/lumenis.js";

dotenv.config();

/* -------------------------------- */
/* PATH SETUP */
/* -------------------------------- */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ROOT_DIR = path.resolve(__dirname, "..");
const FRONTEND_DIR = path.join(ROOT_DIR, "infinity_glass");
const DATA_DIR = path.join(ROOT_DIR, "data");
const BOOT_DIR = path.join(DATA_DIR, "boot");
const BREADCRUMB_DIR = path.join(DATA_DIR, "breadcrumbs");

/* -------------------------------- */
/* CREATE REQUIRED DIRECTORIES */
/* -------------------------------- */

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(BOOT_DIR, { recursive: true });
fs.mkdirSync(BREADCRUMB_DIR, { recursive: true });

/* -------------------------------- */
/* SERVER SETUP */
/* -------------------------------- */

const PORT = Number(process.env.PORT || 3000);

const app = express();
const server = http.createServer(app);

app.use(cors());
app.use(express.json());

/* -------------------------------- */
/* STATIC FRONTEND */
/* -------------------------------- */

app.use(express.static(FRONTEND_DIR));

/* -------------------------------- */
/* BOOT VECTOR */
/* -------------------------------- */

const boot = establishBootVector();
console.log("Boot vector direction:", boot.direction);

/* -------------------------------- */
/* API ROUTES */
/* -------------------------------- */

app.get("/api/status", (req, res) => {
  res.json({
    system: "One2lvOS",
    runtime: "Infinity Glass",
    reactor: "online",
    timestamp: Date.now()
  });
});

/* ---------- WHO.DAT ---------- */

app.get("/api/who.dat", (req, res) => {

  const file = path.join(DATA_DIR, "who.dat.json");

  try {
    const data = JSON.parse(fs.readFileSync(file));
    res.json(data);
  } catch (err) {
    res.status(500).json({
      error: "who.dat unavailable"
    });
  }

});

/* ---------- REACTOR CORE ---------- */

app.post("/api/reactor", (req, res) => {

  const { event, data } = req.body || {};

  if (!event) {
    return res.status(400).json({
      error: "missing event"
    });
  }

  reactor.emitEvent(event, data || {});
  writeBreadcrumb(`reactor event: ${event}`);

  res.json({
    status: "reactor event processed",
    event
  });

});

/* ---------- LUMENIS BUILDER ---------- */

app.post("/api/lumenis/build", (req, res) => {

  const { prompt } = req.body;

  if (!prompt) {
    return res.status(400).json({
      success: false,
      error: "Prompt required"
    });
  }

  try {

    const moduleName = lumenisBuild(prompt);

    reactor.emitEvent("lumenis_build", {
      prompt,
      module: moduleName
    });

    res.json({
      success: true,
      module: moduleName
    });

  } catch (err) {

    console.error("Lumenis build error:", err);

    res.status(500).json({
      success: false,
      error: "Build failed"
    });

  }

});

/* -------------------------------- */
/* LUMENIS AI INJECTION */
/* -------------------------------- */

reactor.on("event", (event, data) => {

  try {

    const result = lumenisBuild(
      `Analyze event: ${event} with data ${JSON.stringify(data)}`
    );

    console.log("🌷 Lumenis AI:", result);

  } catch (err) {

    console.error("Lumenis processing error:", err);

  }

});

/* -------------------------------- */
/* BREADCRUMB LOGGER */
/* -------------------------------- */

function writeBreadcrumb(msg) {

  const entry = `[${new Date().toISOString()}] ${msg}\n`;

  fs.appendFileSync(
    path.join(BREADCRUMB_DIR, "runtime.log"),
    entry
  );

}

/* -------------------------------- */
/* WEBSOCKET SERVER */
/* -------------------------------- */

const wss = new WebSocketServer({ server });

wss.on("connection", ws => {

  console.log("HUD client connected");

  ws.send(JSON.stringify({
    type: "system",
    message: "Infinity Glass HUD connected"
  }));

  ws.on("message", msg => {

    try {

      const data = JSON.parse(msg.toString());

      if (data.event) {
        reactor.emitEvent(data.event, data.payload || {});
      }

    } catch {}

  });

});

/* ---------- BROADCAST REACTOR EVENTS ---------- */

reactor.on("event", (event, data) => {

  const payload = JSON.stringify({
    type: "reactor",
    event,
    data
  });

  wss.clients.forEach(client => {

    if (client.readyState === 1) {
      client.send(payload);
    }

  });

});

/* -------------------------------- */
/* START SERVER */
/* -------------------------------- */

server.listen(PORT, () => {

  console.log(`One2lvOS running on http://127.0.0.1:${PORT}`);

  console.log("=== Infinity Glass Runtime ===");
  console.log("[OPTICS] OK");
  console.log("[SENSORS] OK");
  console.log("[POWER] OK");
  console.log("[HUD] READY");

  writeBreadcrumb("runtime started");

});
