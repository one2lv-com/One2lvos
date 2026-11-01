/* One2lvOS WebOS layer for the Lumenis Reactor desktop.
 * Loaded by one2lvos-desktop.html when served from the reactor (/desktop).
 * - Site Directory: every service, live status from the VM, Access session per hostname,
 *   each opens as a window on its same-origin sub-page (/svc/<id>/...) or on its direct hostname.
 * - Reactor Console: status, council, facts, memory search, checkpoints, VectorFS,
 *   IONOS diagnostics and terminal, all on the reactor's own routes (same origin).
 * - Rewires the old localhost calls: reactor routes same-origin, other services through
 *   the reactor's /svc/<id> proxy, WebSockets on wss://<this host>.
 */
(function () {
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const j = (d) => esc(JSON.stringify(d, null, 2));
    async function getJSON(url, opts) {
        const r = await fetch(url, Object.assign({signal: AbortSignal.timeout(20000), credentials: 'same-origin'}, opts || {}));
        const ct = r.headers.get('content-type') || '';
        if (r.redirected || ct.includes('text/html')) {
            if (r.url.includes('cloudflareaccess.com')) throw new Error('Cloudflare Access session expired: reload the page to sign in');
        }
        const d = ct.includes('json') ? await r.json() : await r.text();
        if (!r.ok) throw new Error((d && d.error) || ('HTTP ' + r.status));
        return d;
    }
    window.O2 = { getJSON, services: [], access: {}, esc };

    // ── Service status, checked from the VM (one Access login on this host covers every sub-page) ──
    async function loadServices() {
        const d = await getJSON('/api/webos/services');
        O2.services = d.services; O2.notInstalled = d.not_installed;
        return d;
    }
    O2.loadServices = loadServices;

    // ── Site Directory window ───────────────────────────────────────────────────────────
    async function renderDirectory() {
        const box = document.getElementById('o2-dir-list');
        const sum = document.getElementById('o2-dir-summary');
        if (!box) return;
        let d;
        try { d = await loadServices(); }
        catch (e) { box.innerHTML = `<div class="text-red-400 p-4">${esc(e.message)}</div>`; return; }
        if (sum) sum.textContent = `${d.up}/${d.total} services up · checked ${new Date().toLocaleTimeString()}`;
        box.innerHTML = d.services.map(s => {
            const up = s.up
                ? `<span class="text-emerald-400"><i class="fas fa-circle text-[8px] mr-1"></i>Up · ${s.ms} ms</span>`
                : `<span class="text-red-400"><i class="fas fa-circle text-[8px] mr-1"></i>Down</span>`;
            const accTxt = `<a href="${s.direct_url}" target="_blank" rel="noopener" class="text-cyan-300 hover:underline"><i class="fas fa-lock mr-1"></i>${esc(s.direct_url.replace('https://','').replace(/\/$/,''))}</a>`;
            return `
            <div class="bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col gap-2">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-black/40 flex items-center justify-center"><i class="${s.icon} ${s.color} text-xl"></i></div>
                <div class="min-w-0 flex-1">
                  <div class="text-white font-semibold text-sm">${esc(s.name)}</div>
                  <div class="text-gray-400 text-[11px] truncate">${esc(s.desc)}</div>
                </div>
              </div>
              <a href="${s.ui_path}" target="_blank" rel="noopener" class="text-[11px] font-mono text-sky-300 hover:underline truncate">${esc(s.ui_path)}</a>
              <div class="flex items-center justify-between text-[11px]">${up}${accTxt}</div>
              <div class="flex gap-2">
                <button onclick="O2.openService('${s.id}')" class="flex-1 bg-cyan-700/70 hover:bg-cyan-600 text-white text-xs rounded-lg py-1.5"><i class="far fa-window-maximize mr-1"></i>Open</button>
                <button onclick="window.open('${s.ui_path}','_blank','noopener')" class="flex-1 bg-white/10 hover:bg-white/20 text-white text-xs rounded-lg py-1.5"><i class="fas fa-external-link-alt mr-1"></i>New tab</button>
              </div>
            </div>`;
        }).join('') + `
            <div class="col-span-full text-[11px] text-gray-500 pt-2">Not installed on this host: ${
                (d.not_installed || []).map(n => esc(n.name) + ' :' + n.port).join(' · ')}</div>`;
    }
    O2.renderDirectory = renderDirectory;

    // Service window: HTML sites open as same-origin sub-pages (/svc/<id>/...) in an iframe;
    // JSON-only APIs show their replies. Direct hostnames stay one click away.
    const JSON_PATHS = {lobby: ['/agents', '/systems', '/messages', '/compilers', '/'],
                        minimax: ['/health', '/api/broadcaster/overlay'],
                        arcade: ['/']};
    O2.openService = async function (id) {
        if (!O2.services.length) { try { await loadServices(); } catch (e) {} }
        const s = O2.services.find(x => x.id === id);
        if (!s) return;
        const appId = 'svc-' + id;
        const footer = `<div class="text-gray-400 text-xs px-3 py-1.5 flex items-center justify-between border-t border-white/10">
              <span><i class="${s.icon} mr-1 ${s.color}"></i>${esc(s.name)} · <span class="font-mono">${esc(s.ui_path)}</span></span>
              <span class="flex gap-3"><button onclick="var f=document.getElementById('o2-svc-frame-${id}'); if(f) f.src=f.src" class="hover:text-white" title="Reload"><i class="fas fa-redo-alt"></i></button>
              <a href="${s.ui_path}" target="_blank" class="hover:text-white" title="Open sub-page in a new tab"><i class="fas fa-external-link-alt"></i></a>
              <a href="${s.direct_url}" target="_blank" rel="noopener" class="hover:text-white" title="Direct endpoint"><i class="fas fa-globe"></i></a></span></div>`;
        let content;
        if (s.kind === 'json' && JSON_PATHS[id]) {
            const btns = JSON_PATHS[id].map(p => `<button onclick="O2.svcGet('${id}','${p}')" class="bg-white/10 hover:bg-white/20 text-white text-xs rounded px-2 py-1 font-mono">${p}</button>`).join('');
            content = `<div class="h-full flex flex-col bg-[#07030f]">
                <div class="p-2 flex flex-wrap gap-2 border-b border-white/10 items-center">${btns}</div>
                <pre id="o2-svc-out-${id}" class="flex-1 overflow-auto p-3 text-xs text-emerald-300 font-mono">Loading…</pre>${footer}</div>`;
        } else {
            content = `<div class="h-full flex flex-col bg-[#07030f]">
                <iframe src="${s.ui_path}" class="flex-1 w-full border-none bg-white" id="o2-svc-frame-${id}"></iframe>${footer}</div>`;
        }
        apps[appId] = {name: s.name, icon: s.icon, color: s.color, width: 960, height: 640, content,
                       onOpen: () => { if (s.kind === 'json' && JSON_PATHS[id]) setTimeout(() => O2.svcGet(id, JSON_PATHS[id][0]), 100); }};
        openApp(appId);
    };
    O2.svcGet = async function (id, path) {
        const out = document.getElementById('o2-svc-out-' + id);
        if (!out) return;
        out.textContent = 'GET /svc/' + id + path + ' …';
        try { const d = await getJSON('/svc/' + id + path); out.innerHTML = typeof d === 'string' ? esc(d) : j(d); }
        catch (e) { out.textContent = '[error] ' + e.message; }
    };

    apps['site-directory'] = {
        name: 'Site Directory', icon: 'fas fa-sitemap', color: 'text-cyan-300', width: 980, height: 660,
        content: `<div class="h-full flex flex-col bg-[#07030f]">
            <div class="bg-gradient-to-r from-cyan-900 to-indigo-900 text-white p-4 flex items-center justify-between border-b border-cyan-800/40">
              <div><h2 class="text-lg font-bold"><i class="fas fa-sitemap mr-2 text-cyan-300"></i>One2lvOS Site Directory</h2>
              <p class="text-cyan-300/70 text-xs mt-0.5" id="o2-dir-summary">Checking services…</p></div>
              <button onclick="O2.renderDirectory()" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg text-xs"><i class="fas fa-sync-alt mr-1"></i>Refresh</button>
            </div>
            <div id="o2-dir-list" class="flex-1 overflow-auto p-4 grid gap-3" style="grid-template-columns:repeat(auto-fill,minmax(270px,1fr));align-content:start">
              <div class="text-gray-400"><i class="fas fa-spinner fa-spin mr-2"></i>Checking…</div></div>
          </div>`,
        onOpen: () => {
            setTimeout(renderDirectory, 100);
            clearInterval(O2._dirTimer);
            O2._dirTimer = setInterval(() => { if (document.getElementById('o2-dir-list')) renderDirectory(); else clearInterval(O2._dirTimer); }, 30000);
        }
    };

    // ── Reactor Console (reactor's own routes) ────────────────────────────────────────
    const RC_TABS = [
        ['status', 'Status', 'fas fa-heartbeat'], ['facts', 'Facts', 'fas fa-brain'], ['memory', 'Memory search', 'fas fa-search'],
        ['checkpoints', 'Checkpoints', 'fas fa-flag'], ['vectorfs', 'VectorFS', 'fas fa-project-diagram'],
        ['ionos', 'IONOS diagnostics', 'fas fa-server'], ['terminal', 'Terminal', 'fas fa-terminal']];
    O2.rc = async function (tab) {
        const out = document.getElementById('o2-rc-out');
        const bar = document.getElementById('o2-rc-input');
        if (!out) return;
        O2._rcTab = tab;
        document.querySelectorAll('[data-o2rc]').forEach(b => b.classList.toggle('bg-cyan-700', b.dataset.o2rc === tab));
        bar.style.display = ['memory', 'terminal', 'checkpoints'].includes(tab) ? 'flex' : 'none';
        const inp = document.getElementById('o2-rc-text');
        inp.placeholder = tab === 'memory' ? 'Search facts and Astra memory…' : tab === 'terminal' ? 'Shell command on the VM (runs as the reactor user)…' : 'Label for a new checkpoint…';
        out.textContent = 'Loading…';
        try {
            if (tab === 'status') out.innerHTML = j(await getJSON('/api/status'));
            else if (tab === 'facts') {
                const d = await getJSON('/api/facts/all');
                out.innerHTML = `${d.count} facts\n\n` + (d.facts || []).slice(-200).reverse().map(f => esc((f.key || f.fact_key || '') + ' = ' + (typeof f.value === 'string' ? f.value : JSON.stringify(f.value)).slice(0, 300))).join('\n');
            }
            else if (tab === 'checkpoints') out.innerHTML = j(await getJSON('/api/checkpoints?limit=20'));
            else if (tab === 'vectorfs') out.innerHTML = j(await getJSON('/vectorfs/stats'));
            else if (tab === 'ionos') { out.textContent = 'Running full IONOS diagnostic (about 5 seconds)…'; const d = await getJSON('/api/ionos/diagnostics?check=all&summary=true'); out.innerHTML = esc(d.summary || d.text || JSON.stringify(d, null, 2)); }
            else out.textContent = tab === 'memory' ? 'Type a query and press Enter.' : tab === 'terminal' ? 'Type a command and press Enter.' : '';
        } catch (e) { out.textContent = '[error] ' + e.message; }
    };
    O2.rcSubmit = async function () {
        const out = document.getElementById('o2-rc-out');
        const inp = document.getElementById('o2-rc-text');
        const v = inp.value.trim(); if (!v) return;
        const post = (url, body) => getJSON(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
        try {
            if (O2._rcTab === 'memory') { out.textContent = 'Searching…'; out.innerHTML = j(await post('/api/tools/memory/search', {query: v, limit: 10})); }
            else if (O2._rcTab === 'terminal') {
                out.textContent += `\n$ ${v}\n`; inp.value = '';
                const d = await post('/api/terminal', {command: v});
                out.textContent += (d.stdout || '') + (d.stderr || '') + (d.error ? '[' + d.error + ']\n' : '') + `[exit ${d.returncode}]\n`;
                out.scrollTop = out.scrollHeight;
            }
            else if (O2._rcTab === 'checkpoints') { const d = await post('/api/checkpoints', {label: v, state: {source: 'webos', label: v}}); inp.value = ''; out.innerHTML = j(d) + '\n\n' + j(await getJSON('/api/checkpoints?limit=20')); }
        } catch (e) { out.textContent += '\n[error] ' + e.message; }
    };
    apps['reactor-console'] = {
        name: 'Reactor Console', icon: 'fas fa-radiation', color: 'text-cyan-300', width: 900, height: 620,
        content: `<div class="h-full flex flex-col bg-[#07030f]">
            <div class="flex flex-wrap gap-1 p-2 border-b border-cyan-900/50">${RC_TABS.map(t =>
                `<button data-o2rc="${t[0]}" onclick="O2.rc('${t[0]}')" class="text-cyan-200 text-xs px-2.5 py-1.5 rounded-lg hover:bg-cyan-800/60"><i class="${t[2]} mr-1"></i>${t[1]}</button>`).join('')}
              <a href="/lumenis-chat" target="_blank" class="ml-auto text-xs text-sky-300 hover:underline self-center">Full chat ↗</a></div>
            <div id="o2-rc-input" class="p-2 gap-2 border-b border-cyan-900/50" style="display:none">
              <input id="o2-rc-text" class="flex-1 bg-black/40 border border-cyan-800/50 text-cyan-100 rounded-lg px-3 py-1.5 text-sm outline-none font-mono" onkeydown="if(event.key==='Enter')O2.rcSubmit()">
              <button onclick="O2.rcSubmit()" class="bg-cyan-700 hover:bg-cyan-600 text-white px-3 rounded-lg text-sm"><i class="fas fa-play"></i></button></div>
            <pre id="o2-rc-out" class="flex-1 overflow-auto p-3 text-xs text-cyan-200 font-mono whitespace-pre-wrap"></pre></div>`,
        onOpen: () => setTimeout(() => O2.rc('status'), 100)
    };

    // ── Rewired reactor functions (the old ones called /health, /tools, /council, /chat on localhost) ──
    const rout = () => document.getElementById('reactor-output');
    window.reactorStatus = async function () {
        const out = rout(); if (!out) return;
        try { const d = await getJSON('/api/status'); out.textContent = '[Status]\n' + JSON.stringify(d, null, 2); }
        catch (e) { out.textContent = '[Lumenis Reactor offline] ' + e.message; }
    };
    window.reactorTools = async function () {
        const out = rout(); if (!out) return;
        try { const d = await getJSON('/api/tools/registry'); out.textContent = '[Tools]\n' + JSON.stringify(d, null, 2); }
        catch (e) { out.textContent = '[Reactor tools error] ' + e.message; }
    };
    window.reactorCouncil = async function () {
        const out = rout(); if (!out) return;
        try { const d = await getJSON('/api/intelligence'); out.textContent = '[ITT Council]\n' + JSON.stringify(d, null, 2); }
        catch (e) { out.textContent = '[Council error] ' + e.message; }
    };
    // Chat over the reactor WebSocket (same host, wss on https)
    window.reactorSend = function () {
        const out = rout(); const inp = document.getElementById('reactor-msg');
        if (!out || !inp) return;
        const msg = inp.value.trim(); if (!msg) return;
        inp.value = '';
        out.textContent = `> ${msg}\n\n`;
        const ws = new WebSocket(O2_WS('/ws'));
        let text = '';
        ws.onopen = () => ws.send(JSON.stringify({action: 'chat', message: msg, session_id: O2._rcSession || undefined}));
        ws.onmessage = (ev) => {
            let m; try { m = JSON.parse(ev.data); } catch { return; }
            if (m.type === 'session_created') O2._rcSession = m.session_id;
            else if (m.type === 'response_chunk') { text += m.text; out.textContent = `> ${msg}\n\n${text}`; out.scrollTop = out.scrollHeight; }
            else if (m.type === 'seat_activity') { if (!text) out.textContent = `> ${msg}\n\n[${m.seat}] thinking…`; }
            else if (m.type === 'processing_done') { out.textContent += `\n\n[seats: ${(m.meta && m.meta.seats_activated || []).join(', ')}]`; ws.close(); }
            else if (m.type === 'error') { out.textContent += `\n[error] ${m.message}`; ws.close(); }
        };
        ws.onerror = () => { out.textContent += '\n[WebSocket error]'; };
    };

    // ── Service checks used by the terminal app and the Services window ───────────────
    window.checkAllServices = async function () {
        let html = '<div class="text-gray-300 mt-2">';
        try {
            const d = await getJSON('/api/webos/services');
            for (const s of d.services) html += `\n  ${s.name.padEnd(24)} [${s.up ? '<span class="text-green-400">UP</span>' : '<span class="text-red-400">DOWN</span>'}] :${s.port}  ${s.ui_path}  ${s.direct_url}`;
            for (const n of d.not_installed) html += `\n  ${n.name.padEnd(24)} [<span class="text-gray-500">NOT INSTALLED</span>] :${n.port}`;
        } catch (e) { html += '\n  ' + esc(e.message); }
        return html + '</div>';
    };
    window.refreshServices = async function () {
        const list = document.getElementById('services-list'); if (!list) return;
        list.innerHTML = '<div class="text-center text-gray-400 py-4"><i class="fas fa-spinner fa-spin mr-2"></i>Checking...</div>';
        try {
            const d = await loadServices();
            list.innerHTML = d.services.map(s => `
              <div class="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center justify-between hover:shadow-md transition-shadow">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white"><i class="${s.icon}"></i></div>
                  <div><div class="font-medium text-gray-800">${esc(s.name)}</div>
                  <div class="text-xs text-gray-500">:${s.port} · <a class="text-blue-500 hover:underline" href="${s.direct_url}" target="_blank">${esc(s.direct_url.replace('https://','').replace(/\/$/,''))}</a></div></div>
                </div>
                <div class="text-right text-xs"><div class="font-bold ${s.up ? 'text-green-500' : 'text-red-500'}">${s.up ? 'ONLINE' : 'OFFLINE'}</div>
                <button onclick="O2.openService('${s.id}')" class="text-blue-600 hover:underline">Open</button></div>
              </div>`).join('') + d.not_installed.map(n => `
              <div class="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center justify-between opacity-60">
                <div class="font-medium text-gray-600">${esc(n.name)} <span class="text-xs text-gray-400">:${n.port}</span></div>
                <div class="text-xs font-bold text-gray-500">NOT INSTALLED</div></div>`).join('');
        } catch (e) { list.innerHTML = `<div class="text-red-500 p-3">${esc(e.message)}</div>`; }
    };

    // Open the directory first on load, after the About window.
    window.addEventListener('load', () => setTimeout(() => openApp('site-directory'), 1200));
})();
