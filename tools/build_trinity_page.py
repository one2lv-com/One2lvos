#!/usr/bin/env python3
"""Build static/trinity.html from the uploaded Trinity Core v9 page (index.html, 2026-11-16 upload).

Keeps the page's look, 3D council scene, panels and genesis tools, and replaces everything that talked to
the Trinity Core Node proxy (socket.io, /api/memory, /api/tool, /api/twitch ...) with the reactor's real
endpoints:
  chat      /ws (action "chat"; response_chunk / seat_activity / processing_done), fallback POST /api/chat
            reading `response`
  boot      GET /api/status (real values, no canned "All systems NOMINAL" log)
  council   GET /api/council/live + /api/status seats (live seat activity and each seat's model)
  memory    POST /api/tools/memory/store, /api/tools/memory/search, GET /api/tools/memory/all
  discord   POST /api/tools/discord/send, GET /api/tools/discord/messages
  tools     GET /engine/tools, POST /engine/call/<tool>  (the engine's own L0-L3 gate; held calls show in
            the approval queue, decided by the owner through /engine/approvals/<id>/<decision>)
Removed: the browser AUTO approval switch (/approval STRICT|BALANCED|PERMISSIVE|AUTO), the model picker
that named models the reactor does not run, the Twitch sender (the reactor has no Twitch endpoint), and the
memory CLEAR button (no wipe endpoint; deleting memory is an owner action).

Usage: build_trinity_page.py <uploaded index.html> [out=static/trinity.html]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BLOCK_A = r"""/* ═══════════════════════════════════════════════════════════
   TOOL REGISTRY — reactor tool engine (/engine/tools), L0-L3 gate on the server
   ═══════════════════════════════════════════════════════════ */
let TOOL_LIST = [];
const TIER_LABEL = ['L0 READ', 'L1 WRITE', 'L2 HELD', 'L3 HELD+CODE'];
async function loadTools() {
  try {
    const r = await fetch(SERVER + '/engine/tools');
    const d = await r.json();
    const list = Array.isArray(d) ? d : (d.tools || []);
    TOOL_LIST = list.map(t => ({ name: t.name, label: t.name, tier: (t.tier ?? t.level ?? 0), desc: t.description || '' }))
      .filter(t => t.name).sort((a, b) => a.tier - b.tier || a.name.localeCompare(b.name));
    renderToolGrid();
    log('TOOLS: ' + TOOL_LIST.length + ' tools from the reactor tool engine');
  } catch (e) { log('TOOLS ERROR: ' + e.message); }
}
function renderToolGrid() {
  const grid = document.getElementById('tool-grid');
  if (!grid) return;
  if (!TOOL_LIST.length) { grid.innerHTML = '<div style="color:var(--text-muted);font-size:10px;">Loading tools…</div>'; return; }
  grid.innerHTML = TOOL_LIST.slice(0, 60).map(t => {
    const cls = t.tier >= 3 ? 'risk-critical' : t.tier >= 2 ? 'risk-high' : '';
    return `<div class="tool-chip ${cls}" title="${esc(t.desc)}" onclick="execTool('${esc(t.name)}')">
      <div class="t-name">${esc(t.label)}</div><div class="t-risk">${TIER_LABEL[t.tier] || ('L' + t.tier)}</div></div>`;
  }).join('');
}
function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
async function execTool(name) {
  const paramsStr = document.getElementById('tool-params').value.trim();
  let params = {};
  if (paramsStr) { try { params = JSON.parse(paramsStr); } catch { params = { text: paramsStr }; } }
  const out = document.getElementById('tool-output');
  out.textContent = `> Calling ${name}…`;
  try {
    const r = await fetch(SERVER + '/engine/call/' + encodeURIComponent(name).replace(/%2F/g, '/'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) });
    const d = await r.json();
    if (d.held_for_approval) {
      renderApproval({ id: d.approval_id, tool: name, tier: d.tier, reason: d.error || 'held for approval', params });
      out.textContent = `> ${name}: held for One2lv's approval (${d.approval_id})`;
    } else displayToolResult(name, d);
    log('TOOL: ' + name + ' → ' + (d.ok ? 'OK' : (d.held_for_approval ? 'HELD' : 'ERR')));
  } catch (e) { out.textContent = '> Error: ' + e.message; }
}
function displayToolResult(tool, result) {
  document.getElementById('tool-output').textContent = '> ' + JSON.stringify(result, null, 2).slice(0, 6000);
}

/* ═══════════════════════════════════════════════════════════
   APPROVAL QUEUE — decided on the server (owner only); no browser auto-approve
   ═══════════════════════════════════════════════════════════ */
function renderApproval(a) {
  if (!a || !a.id || document.getElementById('approval-' + a.id)) return;
  const queue = document.getElementById('approval-queue');
  const tier = Number(String(a.tier ?? '').replace(/\D/g, '')) || 2;
  const div = document.createElement('div');
  div.className = 'approval-card';
  div.id = 'approval-' + a.id;
  div.innerHTML = `
    <span class="risk-badge risk-${tier >= 3 ? 'critical' : 'high'}">L${tier}</span>
    <div style="margin-top:6px;color:var(--accent-cyan);font-weight:700;">${esc(a.tool || a.name)}</div>
    <div style="color:var(--text-muted);font-size:10px;margin:6px 0;">${esc(a.reason || JSON.stringify(a.params || a.args || {}).substring(0, 120))}</div>
    ${tier >= 3 ? '<input type="text" placeholder="confirmation code" id="code-' + esc(a.id) + '" style="width:100%;margin-bottom:6px;background:rgba(0,0,0,.5);border:1px solid var(--glass-border);border-radius:6px;padding:5px;color:var(--text-primary);">' : ''}
    <div class="action-row">
      <button class="action-btn green" onclick="resolveApproval('${esc(a.id)}','approve')" style="min-width:50px;">✓ APPROVE</button>
      <button class="action-btn pink" onclick="resolveApproval('${esc(a.id)}','deny')" style="min-width:50px;">✗ DENY</button>
    </div>`;
  queue.appendChild(div);
  updateApprovalCount();
}
function updateApprovalCount() {
  const n = document.querySelectorAll('.approval-card').length;
  const count = document.getElementById('approval-count');
  count.textContent = n; count.style.display = n ? 'inline' : 'none';
}
async function resolveApproval(id, action) {
  const codeEl = document.getElementById('code-' + id);
  const q = codeEl && codeEl.value ? '?code=' + encodeURIComponent(codeEl.value) : '';
  try {
    const r = await fetch(SERVER + `/engine/approvals/${encodeURIComponent(id)}/${action}` + q, { method: 'POST' });
    const d = await r.json().catch(() => ({}));
    if (r.status === 403) { log('APPROVAL ERROR: owner sign-in required'); return; }
    log('APPROVAL: ' + action.toUpperCase() + ' ' + id + (d.ok === false ? ' — ' + (d.error || 'refused') : ''));
    if (d.ok !== false) { const div = document.getElementById('approval-' + id); if (div) div.remove(); updateApprovalCount(); }
  } catch (e) { log('APPROVAL ERROR: ' + e.message); }
}
async function pollApprovals() {
  try {
    const d = await (await fetch(SERVER + '/engine/approvals')).json();
    (d.approvals || []).forEach(a => renderApproval({ id: a.id || a.approval_id, tool: a.tool || a.name, tier: a.tier, reason: a.reason, params: a.args }));
  } catch (e) { /* reactor busy */ }
}

/* ═══════════════════════════════════════════════════════════
   MEMORY — /api/tools/memory/*
   ═══════════════════════════════════════════════════════════ */
async function refreshMemoryCount() {
  try {
    const s = await (await fetch(SERVER + '/api/status')).json();
    const facts = (s.compass && s.compass.facts) || 0;
    document.getElementById('mem-count').textContent = facts;
    document.getElementById('mem-fill').style.width = Math.min(100, facts / 10000 * 100) + '%';
  } catch (e) { }
}
async function doStore() {
  const text = prompt('Store a fact in Lumenis memory:');
  if (!text) return;
  try {
    const r = await fetch(SERVER + '/api/tools/memory/store', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source: 'trinity_page' }) });
    const d = await r.json();
    log(d.error ? 'MEMORY ERROR: ' + d.error : 'MEMORY: stored (' + (d.stored || 'ok') + ')');
    refreshMemoryCount();
  } catch (e) { log('MEMORY ERROR: ' + e.message); }
}
async function doSearch() {
  const q = prompt('Search Lumenis memory:');
  if (!q) return;
  const el = document.getElementById('memory-entries');
  try {
    const d = await (await fetch(SERVER + '/api/tools/memory/search', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, limit: 8 }) })).json();
    const rows = [].concat(d.results || [], d.local || [], d.astra || []);
    el.innerHTML = rows.slice(0, 12).map(e => {
      const key = e.key || e.source || e.collection || 'fact';
      const val = e.value || e.text || e.content || JSON.stringify(e);
      return `<div class="vfs-entry"><div class="vfs-key">${esc(key)}</div><div class="vfs-val">${esc(String(val).substring(0, 240))}</div></div>`;
    }).join('') || '<div style="color:var(--text-muted);font-size:10px;">No results</div>';
    log('MEMORY: ' + rows.length + ' results for "' + q + '"');
  } catch (e) { log('MEMORY ERROR: ' + e.message); }
}
function doClear() {
  log('MEMORY: wiping memory is not available from this page (owner action on the reactor).');
}

/* ═══════════════════════════════════════════════════════════
   DISCORD — /api/tools/discord/*  (Twitch: no reactor endpoint)
   ═══════════════════════════════════════════════════════════ */
async function sendDiscord() {
  const msg = document.getElementById('discord-msg').value.trim();
  if (!msg) return;
  try {
    const r = await fetch(SERVER + '/api/tools/discord/send', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: msg }) });
    const d = await r.json();
    log(r.ok && !d.error ? 'DISCORD: Message sent' : 'DISCORD: Failed — ' + (d.error || r.status));
    if (r.ok && !d.error) document.getElementById('discord-msg').value = '';
  } catch (e) { log('DISCORD ERROR: ' + e.message); }
}
function sendTwitch() { log('TWITCH: the reactor has no Twitch endpoint yet — nothing sent.'); }
let _discordSeen = new Set();
async function pollDiscord() {
  try {
    const r = await fetch(SERVER + '/api/tools/discord/messages');
    const d = await r.json();
    STATE.discord = r.ok && !d.error ? 'ONLINE' : 'OFFLINE';
    const msgs = d.messages || (Array.isArray(d) ? d : []);
    msgs.slice().reverse().forEach(m => {
      const id = m.id || (m.timestamp + (m.author && (m.author.username || m.author)));
      if (_discordSeen.has(id)) return;
      _discordSeen.add(id);
      addDiscordMsg({ author: (m.author && (m.author.username || m.author)) || '?', timestamp: m.timestamp, content: m.content || '' });
    });
  } catch (e) { STATE.discord = 'OFFLINE'; }
  renderBridgeStatus();
}
function renderBridgeStatus() {
  const el = document.getElementById('bridge-status');
  el.innerHTML = `
    <div class="bridge-pill ${STATE.discord === 'ONLINE' ? 'online' : 'offline'}">
      <div class="bridge-dot ${STATE.discord === 'ONLINE' ? 'online' : ''}"></div>Discord: ${STATE.discord}</div>
    <div class="bridge-pill offline"><div class="bridge-dot"></div>Twitch: NOT BUILT</div>`;
}
function addDiscordMsg(msg) {
  const feed = document.getElementById('discord-feed');
  if (feed.dataset.started !== '1') { feed.innerHTML = ''; feed.dataset.started = '1'; }
  const div = document.createElement('div');
  div.className = 'chat-entry';
  div.innerHTML = `<span class="chat-user">${esc(msg.author)}</span><span class="chat-time">${msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}</span><br>${esc(msg.content)}`;
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}
function addTwitchMsg(msg) { }

/* ═══════════════════════════════════════════════════════════
   AI CHAT — the reactor's lumenis-chat WebSocket (/ws); fallback POST /api/chat (`response`)
   ═══════════════════════════════════════════════════════════ */
let SESSION_ID = sessionStorage.getItem('trinity_session') || null;
function addChatMsg(role, text) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  div.innerHTML = `<div class="sender">${role === 'user' ? 'YOU' : 'COUNCIL'}</div><div>${esc(text).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>')}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}
function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  addChatMsg('user', msg);
  input.value = '';
  const showSeats = document.getElementById('stream-mode').checked;
  const container = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'chat-msg assistant';
  typing.innerHTML = '<div class="sender">COUNCIL</div><div class="typing">Deliberating<span>.</span><span>.</span><span>.</span></div>';
  container.appendChild(typing);
  container.scrollTop = container.scrollHeight;
  const t0 = performance.now();
  if (socket && socket.readyState === 1) {
    const chunks = [];
    socket._turn = {
      chunk(t) { chunks.push(t); typing.querySelector('div:last-child').textContent = chunks.join('').slice(-300); },
      seat(seat, text) { pulseSeat(seat); if (showSeats) log('COUNCIL: [' + seat + '] ' + text); },
      done(meta) {
        typing.remove();
        addChatMsg('assistant', chunks.join(''));
        const secs = ((performance.now() - t0) / 1000).toFixed(1);
        log('COUNCIL: reply in ' + secs + ' s' + (meta && meta.path ? ' via ' + meta.path : '') + (meta && meta.seats_activated ? ' — seats: ' + meta.seats_activated.join(', ') : ''));
      },
      error(m) { typing.remove(); addChatMsg('assistant', 'Council error: ' + m); log('COUNCIL ERROR: ' + m); }
    };
    socket.send(JSON.stringify({ action: 'chat', message: msg, session_id: SESSION_ID }));
  } else {
    fetch(SERVER + '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, session_id: SESSION_ID }) })
      .then(r => r.json())
      .then(r => {
        typing.remove();
        if (r.error) { addChatMsg('assistant', 'Council error: ' + r.error); return; }
        if (r.session_id) { SESSION_ID = r.session_id; sessionStorage.setItem('trinity_session', SESSION_ID); }
        addChatMsg('assistant', r.response || '');
        log('COUNCIL: reply (' + (r.response || '').length + ' chars, HTTP)');
      })
      .catch(e => { typing.remove(); addChatMsg('assistant', 'Reactor not reachable: ' + e.message); });
  }
}

"""

BLOCK_B = r"""/* ═══════════════════════════════════════════════════════════
   TERMINAL (page commands only — nothing here runs on the machine)
   ═══════════════════════════════════════════════════════════ */
function log(msg) {
  const out = document.getElementById('terminal-output');
  if (!out) { console.log(msg); return; }
  const line = document.createElement('div');
  const color = msg.includes('ERROR') ? 'var(--danger)' : msg.includes('GENESIS') ? 'var(--accent-purple)'
    : msg.includes('COUNCIL') ? 'var(--accent-cyan)' : msg.includes('MEMORY') ? 'var(--accent-green)'
    : msg.includes('DISCORD') ? '#9f4' : msg.includes('REACTOR') ? 'var(--accent-amber)' : 'var(--text-secondary)';
  line.style.color = color;
  line.textContent = '> ' + msg;
  out.appendChild(line);
  out.scrollTop = out.scrollHeight;
}
function handleTerminal(e) {
  if (e.key !== 'Enter') return;
  const cmd = e.target.value.trim();
  if (!cmd) return;
  log('$ ' + cmd);
  if (cmd === '/help') {
    log('Commands: /help /status /council /models /approvals /memory /clear  discord <msg>');
    log('Approvals are decided on the reactor (L2/L3 held for One2lv); this page has no auto-approve.');
  } else if (cmd === '/status') {
    refreshStatus(true);
  } else if (cmd === '/council') {
    COUNCIL.forEach(c => log(`${c.emoji} ${c.name} [${c.status}]${c.model ? ' ' + c.model : ''}`));
  } else if (cmd === '/models') {
    Object.entries(STATE.seatModels || {}).forEach(([k, v]) => log(k + ': ' + v));
  } else if (cmd === '/approvals') {
    pollApprovals(); togglePanel('approval-panel');
  } else if (cmd === '/clear') {
    document.getElementById('terminal-output').innerHTML = '';
  } else if (cmd === '/memory') {
    refreshMemoryCount().then(() => log('MEMORY: ' + document.getElementById('mem-count').textContent + ' facts'));
  } else if (cmd.startsWith('discord ')) {
    document.getElementById('discord-msg').value = cmd.slice(8);
    sendDiscord();
  } else {
    log('Unknown: ' + cmd + ' — /help');
  }
  e.target.value = '';
}
"""

BLOCK_C = r"""/* ═══════════════════════════════════════════════════════════
   BOOT — real reactor status (/api/status), no canned log
   ═══════════════════════════════════════════════════════════ */
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }
const SEAT_INDEX = { sentinel: 0, navigator: 1, witness: 2, weaver: 3, forge: 4, oracle: 5, architect: 6 };
function applyStatus(s) {
  const r = s.reactor || {};
  document.getElementById('res-hz').textContent = (r.frequency_hz ?? '–');
  document.getElementById('res-temp').textContent = (r.temperature ?? '–');
  document.getElementById('res-phase').textContent = r.uptime_seconds != null ? Math.round(r.uptime_seconds / 60) + 'm up' : '–';
  document.getElementById('res-nodes').textContent = (s.nodes ? s.nodes.active_workers + '/' + s.nodes.max_concurrent : '–');
  STATE.seatModels = s.seat_models || {};
  (s.seats || []).forEach(seat => {
    const i = SEAT_INDEX[seat.key];
    if (i != null) { COUNCIL[i].model = (seat.model || '').split('/').pop(); COUNCIL[i].desc = seat.role || COUNCIL[i].desc; }
  });
}
async function refreshStatus(verbose) {
  try {
    const s = await (await fetch(SERVER + '/api/status')).json();
    applyStatus(s);
    if (verbose) {
      const r = s.reactor || {};
      log(`REACTOR: model ${r.model} · up ${Math.round((r.uptime_seconds || 0) / 60)} min · pulses ${r.pulse_count}`);
      log(`MEMORY: ${(s.compass || {}).facts} facts · ${(s.compass || {}).sessions} sessions`);
      log('SWARM: ' + ((s.swarm || {}).enabled ? 'on' : 'off'));
    }
    return s;
  } catch (e) { if (verbose) log('REACTOR ERROR: ' + e.message); return null; }
}
async function refreshCouncil() {
  try {
    const d = await (await fetch(SERVER + '/api/council/live')).json();
    let active = 0;
    (d.seats || []).forEach(seat => {
      const i = SEAT_INDEX[seat.seat];
      if (i == null) return;
      COUNCIL[i].status = seat.active ? 'voting' : (seat.fired ? 'online' : 'idle');
      COUNCIL[i].fired = seat.fired;
      if (seat.active) active++;
    });
    document.getElementById('res-council').textContent = active + '/' + ((d.seats || []).length || COUNCIL.length) + ' active';
    renderCouncil();
  } catch (e) { }
}
function pulseSeat(seat) {
  const i = SEAT_INDEX[seat];
  if (i == null || !nodes[i]) return;
  const n = nodes[i]; n.scale.set(1.8, 1.8, 1.8);
  setTimeout(() => n.scale.set(1, 1, 1), 600);
}
async function runAuroraBoot() {
  const logEl = document.getElementById('boot-log');
  const bar = document.getElementById('genesis-bar');
  const line = t => { logEl.textContent += t + '\n'; logEl.scrollTop = logEl.scrollHeight; };
  line('One2lvOS Trinity Core · connecting to the Lumenis reactor…');
  bar.style.width = '20%';
  const s = await refreshStatus(false);
  if (!s) {
    line('Reactor not reachable at ' + SERVER + ' — status unknown.');
  } else {
    const r = s.reactor || {}, c = s.compass || {}, nd = s.nodes || {};
    line(`Reactor: ${r.provider || '?'} · model ${r.model || '?'} · up ${Math.round((r.uptime_seconds || 0) / 60)} min`);
    bar.style.width = '45%'; await delay(150);
    line(`Council: ${(s.seats || []).length} seats · Oracle ${(s.oracle_reactor || {}).model || '?'} · Forge ${(s.forge_reactor || {}).model || '?'}`);
    bar.style.width = '65%'; await delay(150);
    line(`Memory: ${c.facts ?? '?'} facts in ${c.sessions ?? '?'} sessions · workers ${nd.active_workers ?? '?'}/${nd.max_concurrent ?? '?'}`);
    line(`Bridges: Maton ${(s.maton || {}).connected_services ?? 0} services · swarm ${(s.swarm || {}).enabled ? 'on' : 'off'}`);
    const bad = [s.nvidia && s.nvidia.online === false ? 'NVIDIA offline' : '', (s.oracle_reactor || {}).errors ? 'Oracle errors: ' + s.oracle_reactor.errors : ''].filter(Boolean);
    line(bad.length ? 'Warnings: ' + bad.join(' · ') : 'Reactor answered /api/status.');
  }
  bar.style.width = '100%';
  await delay(700);
  document.getElementById('aurora-boot').classList.add('fade');
  await delay(1200);
  document.getElementById('aurora-boot').style.display = 'none';
  log('BOOT: ' + (s ? 'reactor status loaded' : 'reactor not reachable'));
}

/* ═══════════════════════════════════════════════════════════
   LUMENIS-CHAT WEBSOCKET (/ws)
   ═══════════════════════════════════════════════════════════ */
var socket = null;
function connectSocket() {
  const url = SERVER.replace(/^http/, 'ws') + '/ws';
  try { socket = new WebSocket(url); } catch (e) { log('REACTOR ERROR: ' + e.message); return; }
  socket.onopen = () => {
    STATE.connected = true;
    document.getElementById('conn-dot').classList.add('online');
    document.getElementById('conn-label').textContent = 'REACTOR ONLINE';
    log('REACTOR: lumenis-chat connected');
  };
  socket.onclose = () => {
    STATE.connected = false;
    document.getElementById('conn-dot').classList.remove('online');
    document.getElementById('conn-label').textContent = 'OFFLINE';
    if (socket && socket._turn) { socket._turn.error('connection closed'); socket._turn = null; }
    setTimeout(connectSocket, 5000);
  };
  socket.onmessage = ev => {
    let m; try { m = JSON.parse(ev.data); } catch { return; }
    const turn = socket._turn;
    switch (m.type) {
      case 'init': if (m.session_id && !SESSION_ID) { SESSION_ID = m.session_id; sessionStorage.setItem('trinity_session', SESSION_ID); } break;
      case 'ping': socket.send(JSON.stringify({ action: 'ping' })); break;
      case 'response_chunk': if (turn) turn.chunk(m.text || ''); break;
      case 'seat_activity': if (turn) turn.seat(m.seat, m.text || ''); else pulseSeat(m.seat); break;
      case 'processing_done': if (m.session_id) { SESSION_ID = m.session_id; sessionStorage.setItem('trinity_session', SESSION_ID); } if (turn) { turn.done(m.meta || m); socket._turn = null; } refreshCouncil(); break;
      case 'error': if (turn) { turn.error(m.message || 'error'); socket._turn = null; } else log('REACTOR ERROR: ' + (m.message || '')); break;
    }
  };
}

/* ═══════════════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════════════ */
window.addEventListener('DOMContentLoaded', () => {
  try { initThreeJS(); } catch (e) { log('3D view unavailable: ' + e.message); }
  renderCouncil();
  renderToolGrid();
  renderBridgeStatus();
  log('One2lvOS Trinity Core v9 — served by the Lumenis reactor');
  log('Type /help for commands');
  runAuroraBoot().then(() => { refreshCouncil(); loadTools(); refreshMemoryCount(); pollDiscord(); pollApprovals(); });
  connectSocket();
  setInterval(() => { refreshStatus(false); refreshCouncil(); }, 15000);
  setInterval(pollApprovals, 20000);
  setInterval(pollDiscord, 30000);
});
"""


def section_start(lines, title):
    for i, l in enumerate(lines):
        if l.strip() == title and i > 0 and lines[i - 1].lstrip().startswith("/* ═"):
            return i - 1
    raise SystemExit(f"section not found: {title}")


def build(src: Path, out: Path):
    html = src.read_text(encoding="utf-8")
    lines = html.split("\n")
    a = section_start(lines, "TOOL REGISTRY")
    b = section_start(lines, "TERMINAL")
    c = section_start(lines, "WINDOW MANAGER")
    d = section_start(lines, "BOOT SEQUENCE")
    end = max(i for i, l in enumerate(lines) if l.strip() == "</script>")
    lines = lines[:a] + BLOCK_A.split("\n") + BLOCK_B.split("\n") + lines[c:d] + BLOCK_C.split("\n") + lines[end:]
    html = "\n".join(lines)

    # The upload's star field line is missing a ')' - a syntax error that stopped the page's whole script.
    # Four lines in the upload's 3D scene each miss a closing ')' - syntax errors that stopped the whole script.
    for frag in ("color: 0xaaddff, size: 0.3, transparent: true, opacity: 0.7 })",
                 "color: 0xa855f7, transparent: true, opacity: 0.4 }",
                 "color: def.color, transparent: true, opacity: 0.15 }",
                 "color: def.color, transparent: true, opacity: 0.12 }"):
        html = html.replace(frag + ");\n", frag + "));\n", 1)
    # STATE: no browser approval mode, no model choice
    html = re.sub(r"approvalMode: 'BALANCED', selectedModel: 'nvidia',\s*", "seatModels: {}, ", html)
    # Model picker -> read-only note; streaming checkbox -> seat activity
    html = re.sub(r'<select class="model-select" id="model-select">.*?</select>',
                  '<div class="model-select" id="model-select" style="font-size:10px;">Council chooses: each seat answers '
                  'with its own model (/models in the terminal). Multi-part messages run as a parallel swarm.</div>',
                  html, flags=re.S)
    html = html.replace('<input type="checkbox" id="stream-mode"> Streaming mode',
                        '<input type="checkbox" id="stream-mode" checked> Show seat activity in the log')
    # Twitch sender: no reactor endpoint
    html = html.replace('placeholder="Message to Twitch..."', 'placeholder="Twitch: not built in the reactor yet" disabled')
    html = html.replace("Waiting for Twitch messages...", "No Twitch bridge in the reactor yet.")
    # Clear button: no wipe endpoint
    html = html.replace('<button class="action-btn pink" onclick="doClear()">CLEAR</button>', '')
    # Canned texts that claimed live connections
    html = html.replace("&gt; Select a tool to execute. API proxy connected.", "&gt; Select a tool. L2/L3 tools are held for One2lv's approval.")
    html = html.replace("> Select a tool to execute. API proxy connected.", "> Select a tool. L2/L3 tools are held for One2lv's approval.")
    html = html.replace("> Trinity Core VFS initialized via proxy server.", "> VFS: not connected to the reactor (no endpoint yet).")
    html = html.replace("All 7 seats acknowledge the resonance threshold before every pulse. The ITT Council convenes at 73Hz.",
                        "Live seat activity from /api/council/live; each seat shows the model it really calls.")
    html = html.replace('<span id="conn-label">CONNECTING</span>', '<span id="conn-label">CONNECTING</span>')
    # Genesis encode posted to the old proxy's /api/memory/store: keep it local
    html = re.sub(r"\n\s*fetch\(SERVER \+ '/api/memory/store'.*?\}\)\s*\}\);", "", html, flags=re.S)
    html = html.replace("const SERVER = window.location.origin; // Auto-detect proxy server",
                        "const SERVER = window.location.origin; // served by the Lumenis reactor")
    # Council seat card shows the real model
    html = html.replace("<span>W:${c.weight}</span>", "<span>${c.model || ''}</span>")
    # Unit labels for the live strip
    html = html.replace('<span class="res-val" id="res-hz">73</span><span>Hz</span>', '<span class="res-val" id="res-hz">–</span><span>Hz</span>')
    html = html.replace('<span class="res-val purple" id="res-temp">18.000</span><span>°C</span>', '<span class="res-val purple" id="res-temp">–</span><span>temp</span>')
    html = html.replace('<span class="res-val pink">φ</span><span id="res-phase">9.6</span>', '<span id="res-phase">–</span>')
    html = html.replace('<span class="res-val" id="res-nodes">7</span>', '<span class="res-val" id="res-nodes">–</span>')
    html = html.replace('<span class="res-val" id="res-council">7/7</span>', '<span class="res-val" id="res-council">–</span>')
    html = html.replace("<title>", "<!-- Built by tools/build_trinity_page.py from the Trinity Core v9 upload (2026-11-16). -->\n<title>", 1)

    for banned in ("socket.io", "io(SERVER", "approvalMode", "All systems NOMINAL", "/api/memory/store", "/api/tool'",
                   "/api/twitch", "r.reply", "nvapi-", "corsproxy"):
        if banned in html:
            raise SystemExit(f"left in the page: {banned}")
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "static" / "trinity.html"
    build(src, out)
