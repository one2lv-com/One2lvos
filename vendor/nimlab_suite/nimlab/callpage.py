"""The browser call page the test server hosts at /call?t=<token>.

Plain HTML and JavaScript, no build step, no CDN. It talks to the same
single model on POST /v1/chat/completions: the microphone audio goes up as an
input_audio part (16 kHz mono WAV made in the page), the reply comes back
as text plus message.audio (modalities ["text", "audio"]) and is played.
Hands-free mode finds speech by loudness (simple voice-activity detection);
tap-to-talk records while the button is held. Talking while a reply plays
stops the reply (barge-in). Files can be attached to any turn.

The token in the link is derived from the server's API key (server.
call_token), and the page sends it as its Bearer key. Chrome only allows the
microphone on https or on localhost / 127.0.0.1.
"""

import html
import json


def denied_html():
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
            "<title>Call page</title><body style='font-family:sans-serif;padding:2em;background:#111;color:#eee'>"
            "<h2>Link not valid</h2><p>Open the call link that <code>./start.sh serve info</code> prints. "
            "Links stop working when the server key is regenerated.</p></body>")


def page_html(model, token, version=""):
    cfg = json.dumps({"model": model, "token": token}).replace("</", "<\\/")
    return _PAGE.replace("__CFG__", cfg).replace("__TITLE__", html.escape(model)).replace(
        "__VERSION__", html.escape(version))


_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Call: __TITLE__</title>
<style>
:root{color-scheme:dark}
body{margin:0;font-family:system-ui,sans-serif;background:#0f1115;color:#e8e8e8;display:flex;flex-direction:column;height:100vh}
header{padding:10px 14px;background:#171a21;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
header b{font-size:17px}#state{font-size:13px;color:#9aa}
#log{flex:1;overflow-y:auto;padding:12px}
.msg{max-width:88%;margin:6px 0;padding:8px 11px;border-radius:12px;white-space:pre-wrap;word-wrap:break-word;line-height:1.35}
.me{background:#2b4b7e;margin-left:auto}.it{background:#22262f}.sys{color:#9aa;font-size:12px;text-align:center;max-width:100%}
.msg img{max-width:100%;border-radius:8px;display:block;margin-top:6px}.msg a{color:#8cf}
.lat{font-size:11px;color:#8a9;margin-top:4px}
footer{padding:10px;background:#171a21;display:flex;flex-direction:column;gap:8px}
.row{display:flex;gap:8px;align-items:center}
button,select{background:#2a2f3a;color:#eee;border:0;border-radius:10px;padding:10px 12px;font-size:15px}
#talk{flex:1;font-size:18px;padding:16px;background:#2f6b3f;touch-action:none;user-select:none}
#talk.live{background:#b0353a}#talk.busy{background:#6b5a2f}
#text{flex:1;background:#0f1115;color:#eee;border:1px solid #333;border-radius:10px;padding:10px;font-size:15px}
#meter{height:6px;background:#222;border-radius:3px;overflow:hidden}#meter i{display:block;height:100%;width:0;background:#4c9}
#files{font-size:12px;color:#9aa}
</style></head><body>
<header><b>__TITLE__</b><span id="state">tap Start</span>
<select id="mode"><option value="vad">Hands-free</option><option value="ptt">Tap to talk</option></select>
<label style="font-size:13px"><input type="checkbox" id="speak" checked> voice replies</label>
<button id="end">End call</button></header>
<div id="log"><div class="msg sys">One entity, one endpoint. Start the call and talk; attach files with the clip button. __VERSION__</div></div>
<footer>
<div id="meter"><i></i></div>
<div class="row"><button id="talk">Start call</button></div>
<div class="row"><button id="clip" title="Attach files">&#128206;</button>
<input id="pick" type="file" multiple hidden>
<input id="text" placeholder="or type a message" autocomplete="off"><button id="send">Send</button></div>
<div id="files"></div>
</footer>
<script>
"use strict";
const CFG = __CFG__;
const API = location.origin + "/v1/chat/completions";
const $ = (id) => document.getElementById(id);
const history = [];
let attached = [];
let ctx = null, src = null, proc = null, stream = null;
let live = false, busy = false, capturing = false, pttDown = false;
let chunks = [], preroll = [], loudMs = 0, quietMs = 0, speechMs = 0, floor = 0.01;
let player = null;
const RATE = 16000;

function setState(t) { $("state").textContent = t; }
function esc(s) { return s.replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c])); }
function withKey(u) {
  if (u.startsWith(location.origin + "/v1/files/") || u.startsWith("/v1/files/")) return u + (u.includes("?") ? "&" : "?") + "key=" + CFG.token;
  return u;
}
function render(text) {
  let h = esc(text);
  h = h.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, a, u) => '<img alt="' + a + '" src="' + withKey(u) + '">');
  h = h.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, a, u) => {
    const k = withKey(u);
    if (/^Listen/.test(a)) return '<a href="' + k + '" target="_blank">' + a + '</a><audio controls src="' + k + '"></audio>';
    return '<a href="' + k + '" target="_blank">' + a + '</a>';
  });
  return h;
}
function add(cls, text, lat) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.innerHTML = cls === "it" ? render(text) : esc(text);
  if (lat) { const l = document.createElement("div"); l.className = "lat"; l.textContent = lat; d.appendChild(l); }
  $("log").appendChild(d);
  $("log").scrollTop = 1e9;
  return d;
}

// ---- audio capture -----------------------------------------------------
async function startCall() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    add("sys", "This browser has no microphone access here. Chrome allows it only on https or on localhost / 127.0.0.1.");
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
  } catch (e) { add("sys", "Microphone refused: " + e.message); return; }
  ctx = new (window.AudioContext || window.webkitAudioContext)();
  src = ctx.createMediaStreamSource(stream);
  proc = ctx.createScriptProcessor(4096, 1, 1);
  proc.onaudioprocess = onAudio;
  src.connect(proc); proc.connect(ctx.destination);
  live = true;
  $("talk").textContent = $("mode").value === "vad" ? "Listening... (tap to mute)" : "Hold to talk";
  setState("call live");
}
function endCall() {
  live = false; capturing = false;
  if (proc) { proc.disconnect(); proc = null; }
  if (src) { src.disconnect(); src = null; }
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  if (ctx) { ctx.close(); ctx = null; }
  stopPlayback();
  $("talk").textContent = "Start call"; $("talk").className = "";
  setState("call ended");
}
function onAudio(ev) {
  const x = ev.inputBuffer.getChannelData(0);
  const buf = new Float32Array(x);
  let sum = 0; for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
  const rms = Math.sqrt(sum / buf.length);
  const ms = 1000 * buf.length / ctx.sampleRate;
  $("meter").firstChild.style.width = Math.min(100, rms * 400) + "%";
  const playing = player && !player.paused;
  if ($("mode").value === "ptt") {
    if (pttDown) chunks.push(buf);
    return;
  }
  if (busy && !playing) return;
  const thr = Math.max(0.015, floor * 3) * (playing ? 2.5 : 1);
  if (!capturing) {
    floor = rms < floor * 2 ? floor * 0.95 + rms * 0.05 : floor;
    preroll.push(buf); if (preroll.length > 4) preroll.shift();
    loudMs = rms > thr ? loudMs + ms : 0;
    if (loudMs >= 180) {
      if (playing) { stopPlayback(); add("sys", "(you cut in)"); }
      capturing = true; chunks = preroll.slice(); preroll = []; quietMs = 0; speechMs = loudMs;
      $("talk").className = "live"; setState("hearing you");
    }
    return;
  }
  chunks.push(buf);
  if (rms > thr * 0.7) { quietMs = 0; speechMs += ms; } else { quietMs += ms; }
  if (quietMs > 900 || speechMs > 30000) {
    capturing = false; loudMs = 0;
    $("talk").className = "";
    if (speechMs >= 400) sendAudio(chunks); else setState("call live");
    chunks = [];
  }
}
function toWav(bufs, inRate) {
  let n = 0; bufs.forEach((b) => n += b.length);
  const all = new Float32Array(n); let o = 0; bufs.forEach((b) => { all.set(b, o); o += b.length; });
  const ratio = inRate / RATE, len = Math.floor(n / ratio);
  const pcm = new Int16Array(len);
  for (let i = 0; i < len; i++) {
    const a = Math.floor(i * ratio), b = Math.min(n, Math.floor((i + 1) * ratio));
    let s = 0; for (let j = a; j < b; j++) s += all[j];
    const v = Math.max(-1, Math.min(1, s / Math.max(1, b - a)));
    pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  const buf = new ArrayBuffer(44 + pcm.length * 2), dv = new DataView(buf);
  const w = (p, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(p + i, s.charCodeAt(i)); };
  w(0, "RIFF"); dv.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, RATE, true); dv.setUint32(28, RATE * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
  w(36, "data"); dv.setUint32(40, pcm.length * 2, true);
  new Int16Array(buf, 44).set(pcm);
  return new Uint8Array(buf);
}
function b64(bytes) {
  let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

// ---- files ----------------------------------------------------------------
function readFile(f) {
  return new Promise((ok, bad) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = bad; r.readAsDataURL(f); });
}
async function fileParts() {
  const parts = [];
  for (const f of attached) {
    const url = await readFile(f);
    const t = f.type || "";
    if (t.startsWith("image/")) parts.push({type: "image_url", image_url: {url}});
    else if (t.startsWith("video/")) parts.push({type: "video_url", video_url: {url}});
    else if (t.startsWith("audio/")) {
      const fmt = (f.name.split(".").pop() || "wav").toLowerCase();
      parts.push({type: "input_audio", input_audio: {data: url.split(",")[1], format: fmt}});
    } else parts.push({type: "file", file: {filename: f.name, file_data: url}});
  }
  return parts;
}
function showFiles() { $("files").textContent = attached.length ? "Attached: " + attached.map((f) => f.name).join(", ") + "  (tap the clip to change)" : ""; }

// ---- one turn ---------------------------------------------------------------
async function sendAudio(bufs) {
  const wav = toWav(bufs, ctx.sampleRate);
  await turn([{type: "input_audio", input_audio: {data: b64(wav), format: "wav"}}], null);
}
async function sendText() {
  const t = $("text").value.trim();
  if (!t && !attached.length) return;
  $("text").value = "";
  await turn(t ? [{type: "text", text: t}] : [], t);
}
async function turn(parts, typed) {
  if (busy) return;
  busy = true; $("talk").classList.add("busy"); setState("thinking");
  const files = await fileParts();
  const names = attached.map((f) => f.name);
  attached = []; showFiles();
  const me = add("me", (typed || "(speaking...)") + (names.length ? "\n[" + names.join(", ") + "]" : ""));
  const content = parts.concat(files);
  const body = {model: CFG.model, messages: history.concat([{role: "user", content}])};
  if ($("speak").checked) { body.modalities = ["text", "audio"]; body.audio = {voice: "alloy", format: "wav"}; }
  const t0 = performance.now();
  try {
    const r = await fetch(API, {method: "POST", headers: {"Content-Type": "application/json", "Authorization": "Bearer " + CFG.token}, body: JSON.stringify(body)});
    const j = await r.json();
    if (!r.ok) throw new Error((j.error && j.error.message) || ("HTTP " + r.status));
    const msg = j.choices[0].message;
    const said = (j.testbed && j.testbed.transcript) || typed || "(voice)";
    if (!typed) me.textContent = said + (names.length ? "\n[" + names.join(", ") + "]" : "");
    history.push({role: "user", content: said + (names.length ? " [attached: " + names.join(", ") + "]" : "")});
    history.push({role: "assistant", content: msg.content || ""});
    const total = Math.round(performance.now() - t0);
    const tr = (j.testbed_trace || []).map((s) => s.role + " " + s.ms + " ms").join(" | ");
    add("it", msg.content || "", "total " + total + " ms" + (tr ? "  |  " + tr : ""));
    if (msg.audio && msg.audio.data) play(msg.audio.data);
  } catch (e) {
    add("sys", "Error: " + e.message);
  } finally {
    busy = false; $("talk").classList.remove("busy");
    setState(live ? "call live" : "ready");
  }
}
function play(b64data) {
  stopPlayback();
  const bin = atob(b64data), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  player = new Audio(URL.createObjectURL(new Blob([u], {type: "audio/wav"})));
  player.play().catch((e) => add("sys", "Couldn't play the reply: " + e.message));
  setState("speaking (talk to cut in)");
  player.onended = () => setState(live ? "call live" : "ready");
}
function stopPlayback() { if (player) { player.pause(); player = null; } }

// ---- controls ---------------------------------------------------------------
$("talk").addEventListener("click", () => {
  if (!live) { startCall(); return; }
  if ($("mode").value === "vad") endCall();
});
const down = (e) => { if (!live || $("mode").value !== "ptt") return; e.preventDefault(); stopPlayback(); pttDown = true; chunks = []; $("talk").className = "live"; setState("recording"); };
const up = () => { if (!pttDown) return; pttDown = false; $("talk").className = ""; const c = chunks; chunks = []; if (c.length > 2) sendAudio(c); else setState("call live"); };
$("talk").addEventListener("pointerdown", down);
$("talk").addEventListener("pointerup", up);
$("talk").addEventListener("pointerleave", up);
$("mode").addEventListener("change", () => { if (live) $("talk").textContent = $("mode").value === "vad" ? "Listening... (tap to end)" : "Hold to talk"; });
$("end").addEventListener("click", endCall);
$("send").addEventListener("click", sendText);
$("text").addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });
$("clip").addEventListener("click", () => $("pick").click());
$("pick").addEventListener("change", () => { attached = Array.from($("pick").files); $("pick").value = ""; showFiles(); });
</script></body></html>
"""
