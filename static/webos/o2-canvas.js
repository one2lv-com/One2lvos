/* One2lvOS Canvas: a page-building workspace for the desktop.
 *
 * One2lvOS's own Canvas-style editor (not Google's Gemini Canvas): a project of HTML, CSS and JS
 * files, a code editor, a live preview and an optional AI helper.
 *
 * Files   : saved on this server in One2lvOS Files (the WebDAV share), under /canvas/<project>/,
 *           through the Network Manager service's WebDAV API (same origin, /svc/network).
 *           Unsaved edits are kept as drafts in this browser (localStorage) until saved.
 * Preview : a sandboxed iframe (scripts allowed, no same-origin), so a page in the preview cannot
 *           reach the desktop, its sign-in or the One2lvOS APIs. Linked style.css / script.js files
 *           from the project are inlined into the preview.
 * AI      : optional. Sends the instruction and the open file to the reactor's
 *           /api/tools/nvidia/infer (Lumenis's NVIDIA model). Replies are capped at about 1024 tokens.
 */
(function () {
    'use strict';
    const NET = '/svc/network/api/network/connections/one2lv-files/webdav';
    const ROOT = '/canvas';
    const AI_URL = '/api/tools/nvidia/infer';
    const CM_BASE = 'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/';
    const TEXT_EXT = ['html', 'htm', 'css', 'js', 'mjs', 'json', 'md', 'txt', 'svg', 'xml'];
    const NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,63}$/;
    const MAX_BYTES = 2 * 1024 * 1024;
    const AI_MAX_CHARS = 12000;
    const LS = 'o2canvas:';

    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
    const ext = (n) => (String(n).split('.').pop() || '').toLowerCase();
    const isText = (n) => n.includes('.') && TEXT_EXT.includes(ext(n));
    const $ = (id) => document.getElementById(id);

    const S = {
        project: null, projects: [], files: [], file: null, previewEntry: null,
        buf: {}, saved: {}, docs: {}, cm: null, ta: null, auto: true, view: 'split',
        aiUndo: null, timer: null, draftTimer: null, busy: false
    };
    if ((window.innerWidth || 1200) < 760) S.view = 'code';

    // ── WebDAV through the Network Manager service ──────────────────────────────────────
    async function dav(op, opts, path) {
        const url = NET + '/' + op + (path != null ? '?path=' + encodeURIComponent(path) : '');
        const r = await fetch(url, Object.assign({credentials: 'same-origin', signal: AbortSignal.timeout(20000)}, opts || {}));
        if (r.redirected && r.url.includes('cloudflareaccess.com')) throw new Error('Cloudflare sign-in expired: reload the page');
        if (!r.ok) {
            let m = '';
            try { const d = await r.json(); m = d.error || ''; } catch (e) {}
            const err = new Error(m || ('HTTP ' + r.status));
            err.status = r.status;
            throw err;
        }
        return r;
    }
    const is404 = (e) => e && (e.status === 404 || /404|not found/i.test(e.message || ''));
    const davList = async (p) => (await dav('list', null, p)).json();
    const davRead = async (p) => (await dav('get', null, p)).text();
    const davWrite = (p, t) => dav('put', {method: 'PUT', headers: {'Content-Type': 'application/octet-stream'}, body: new Blob([t], {type: 'text/plain'})}, p);
    const davMkdir = (p) => dav('mkdir', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path: p})});
    const davMove = (a, b) => dav('move', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({from: a, to: b})});
    const davDelete = (p) => dav('delete', {method: 'DELETE'}, p);
    const fpath = (f, proj) => ROOT + '/' + (proj || S.project) + '/' + f;

    // ── Drafts on this device ─────────────────────────────────────────────────────────────
    const dkey = (f) => LS + 'draft:' + S.project + '/' + f;
    function draftGet(f) { try { return localStorage.getItem(dkey(f)); } catch (e) { return null; } }
    function draftSet(f, t) { try { localStorage.setItem(dkey(f), t); } catch (e) {} }
    function draftDel(f) { try { localStorage.removeItem(dkey(f)); } catch (e) {} }
    const dirty = (f) => S.buf[f] != null && S.buf[f] !== S.saved[f];
    const anyDirty = () => S.files.some(dirty);

    function status(msg, kind) {
        const s = $('o2c-status');
        if (!s) return;
        s.textContent = msg;
        s.style.color = kind === 'err' ? '#fca5a5' : kind === 'ok' ? '#86efac' : '#9ca3af';
    }
    const now = () => new Date().toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});

    // ── Starter project ───────────────────────────────────────────────────────────────────
    function starter(name) {
        return {
            'index.html': `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${name}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>${name}</h1>
    <p>Edit index.html, style.css and script.js. The preview updates as you type.</p>
    <button id="btn">Click me</button>
    <p id="out"></p>
  </main>
  <script src="script.js"></script>
</body>
</html>
`,
            'style.css': `body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #0b1020;
  color: #e5e7eb;
}
main {
  max-width: 640px;
  margin: 48px auto;
  padding: 0 20px;
}
button {
  padding: 8px 16px;
  border: 0;
  border-radius: 8px;
  background: #6366f1;
  color: white;
  cursor: pointer;
}
`,
            'script.js': `let clicks = 0;
document.getElementById('btn').addEventListener('click', () => {
  clicks++;
  document.getElementById('out').textContent = 'Clicked ' + clicks + ' time' + (clicks === 1 ? '' : 's');
  console.log('clicks:', clicks);
});
`
        };
    }
    function blankFor(name) {
        const e = ext(name);
        if (e === 'html' || e === 'htm') return `<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <title>${name.replace(/\.[^.]+$/, '')}</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n</body>\n</html>\n`;
        if (e === 'json') return '{}\n';
        if (e === 'svg') return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">\n  <circle cx="50" cy="50" r="40" fill="#6366f1"/>\n</svg>\n';
        return '';
    }

    // ── Editor (CodeMirror from cdnjs, plain textarea if it cannot load) ────────────────
    let cmLoading = null;
    function loadCM() {
        if (window.CodeMirror && window.CodeMirror.modes && window.CodeMirror.modes.htmlmixed) return Promise.resolve(true);
        if (cmLoading) return cmLoading;
        ['codemirror.min.css', 'theme/material-darker.min.css'].forEach(h => {
            const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = CM_BASE + h; document.head.appendChild(l);
        });
        const load = (src) => new Promise((res, rej) => {
            const s = document.createElement('script'); s.src = CM_BASE + src; s.onload = res; s.onerror = rej; document.head.appendChild(s);
        });
        cmLoading = load('codemirror.min.js')
            .then(() => Promise.all(['mode/xml/xml.min.js', 'mode/javascript/javascript.min.js', 'mode/css/css.min.js',
                'mode/markdown/markdown.min.js', 'addon/fold/xml-fold.min.js', 'addon/edit/closebrackets.min.js',
                'addon/edit/matchbrackets.min.js'].map(load)))
            .then(() => Promise.all(['mode/htmlmixed/htmlmixed.min.js', 'addon/edit/closetag.min.js'].map(load)))
            .then(() => true).catch(() => false);
        return cmLoading;
    }
    function modeFor(f) {
        const e = ext(f);
        if (e === 'html' || e === 'htm') return 'htmlmixed';
        if (e === 'svg' || e === 'xml') return 'xml';
        if (e === 'css') return 'css';
        if (e === 'js' || e === 'mjs') return 'javascript';
        if (e === 'json') return {name: 'javascript', json: true};
        if (e === 'md') return 'markdown';
        return null;
    }
    async function setupEditor() {
        const host = $('o2c-editor');
        if (!host) return;
        host.innerHTML = '';
        S.cm = null; S.ta = null; S.docs = {};
        const ok = await loadCM();
        if (!$('o2c-editor')) return;
        if (ok && window.CodeMirror) {
            S.cm = window.CodeMirror(host, {
                value: '', theme: 'material-darker', lineNumbers: true, lineWrapping: false, tabSize: 2, indentUnit: 2,
                autoCloseTags: true, autoCloseBrackets: true, matchBrackets: true,
                extraKeys: {'Ctrl-S': () => saveFile(S.file), 'Cmd-S': () => saveFile(S.file),
                    'Tab': (cm) => cm.somethingSelected() ? cm.indentSelection('add') : cm.replaceSelection('  ', 'end')}
            });
            S.cm.setSize('100%', '100%');
            S.cm.on('change', () => onEdit());
        } else {
            const ta = document.createElement('textarea');
            ta.spellcheck = false;
            ta.className = 'w-full h-full bg-[#1e1e1e] text-gray-100 font-mono text-[13px] leading-5 p-3 outline-none resize-none';
            ta.addEventListener('input', onEdit);
            ta.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); saveFile(S.file); }
                else if (e.key === 'Tab') {
                    e.preventDefault();
                    const a = ta.selectionStart, b = ta.selectionEnd;
                    ta.value = ta.value.slice(0, a) + '  ' + ta.value.slice(b);
                    ta.selectionStart = ta.selectionEnd = a + 2; onEdit();
                }
            });
            host.appendChild(ta);
            S.ta = ta;
            status('Code editor could not load from the CDN, so a plain text editor is in use.', 'err');
        }
    }
    function editorShow(f) {
        const text = S.buf[f] != null ? S.buf[f] : '';
        if (S.cm) {
            if (!S.docs[f]) S.docs[f] = window.CodeMirror.Doc(text, modeFor(f));
            S.cm.swapDoc(S.docs[f]);
            S.cm.setOption('readOnly', false);
            setTimeout(() => S.cm && S.cm.refresh(), 0);
        } else if (S.ta) {
            S.ta.value = text; S.ta.disabled = false;
        }
    }
    function editorValue() { return S.cm ? S.cm.getValue() : S.ta ? S.ta.value : ''; }
    function editorReplace(text) {
        // Undoable with Ctrl+Z as well as the Undo AI change button.
        if (S.cm) { S.cm.getDoc().setValue(text); }
        else if (S.ta) { S.ta.value = text; onEdit(); }
    }

    function onEdit() {
        if (!S.file) return;
        S.buf[S.file] = editorValue();
        clearTimeout(S.draftTimer);
        const f = S.file;
        S.draftTimer = setTimeout(() => { if (dirty(f)) draftSet(f, S.buf[f]); else draftDel(f); }, 400);
        renderFiles(); renderTab();
        if (S.auto) { clearTimeout(S.timer); S.timer = setTimeout(refreshPreview, 600); }
    }

    // ── Preview ───────────────────────────────────────────────────────────────────────────
    const HELPER = `<script>(function(){var P=function(t,m){try{parent.postMessage({o2canvas:t,msg:String(m)},'*')}catch(e){}};` +
        `['log','info','warn','error'].forEach(function(k){var o=console[k];console[k]=function(){try{P(k,[].map.call(arguments,function(a){try{return typeof a==='object'?JSON.stringify(a):String(a)}catch(e){return String(a)}}).join(' '))}catch(e){}return o.apply(console,arguments)}});` +
        `window.addEventListener('error',function(e){P('error',(e.message||'Error')+(e.lineno?' (line '+e.lineno+')':''))});` +
        `window.addEventListener('unhandledrejection',function(e){P('error','Unhandled promise rejection: '+((e.reason&&e.reason.message)||e.reason))});` +
        `document.addEventListener('click',function(e){var a=e.target&&e.target.closest&&e.target.closest('a[href]');if(!a)return;var h=a.getAttribute('href')||'';` +
        `if(/^([a-z]+:|\\/\\/|#)/i.test(h)||a.target==='_blank')return;e.preventDefault();P('nav',h)},true);})();<\/script>`;

    function projFile(ref) {
        if (!ref) return null;
        ref = ref.trim();
        if (/^([a-z]+:|\/\/|#|\/)/i.test(ref)) return null;
        let clean = ref.replace(/^\.\//, '').split(/[?#]/)[0];
        try { clean = decodeURIComponent(clean); } catch (e) {}
        return S.files.includes(clean) ? clean : null;
    }
    const attr = (s) => String(s).replace(/["&<>]/g, c => ({'"': '&quot;', '&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));
    function buildPage(entry, forExport) {
        let html = S.buf[entry] || '';
        html = html.replace(/<link\b[^>]*>/gi, (tag) => {
            if (!/rel\s*=\s*["']?stylesheet/i.test(tag)) return tag;
            const m = tag.match(/href\s*=\s*["']([^"']+)["']/i);
            const f = m && projFile(m[1]);
            if (!f || S.buf[f] == null) return tag;
            return '<style data-file="' + attr(f) + '">\n' + S.buf[f].replace(/<\/style/gi, '<\\/style') + '\n</style>';
        });
        html = html.replace(/<script\b([^>]*?)\bsrc\s*=\s*["']([^"']+)["']([^>]*)>\s*<\/script>/gi, (all, a, src, b) => {
            const f = projFile(src);
            if (!f || S.buf[f] == null) return all;
            const attrs = (a + ' ' + b).replace(/\s+/g, ' ').trim();
            return '<script' + (attrs ? ' ' + attrs : '') + ' data-file="' + attr(f) + '">\n' + S.buf[f].replace(/<\/script/gi, '<\\/script') + '\n</script>';
        });
        html = html.replace(/(<img\b[^>]*?\bsrc\s*=\s*["'])([^"']+)(["'])/gi, (all, p, src, q) => {
            const f = projFile(src);
            if (!f || ext(f) !== 'svg' || S.buf[f] == null) return all;
            return p + 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(S.buf[f]) + q;
        });
        if (!forExport) {
            const m = html.match(/<head[^>]*>/i);
            html = m ? html.slice(0, m.index + m[0].length) + HELPER + html.slice(m.index + m[0].length) : HELPER + html;
        }
        return html;
    }
    function entryFile() {
        if (S.previewEntry && S.files.includes(S.previewEntry)) return S.previewEntry;
        if (S.file && /^(html|htm)$/.test(ext(S.file))) return S.file;
        if (S.files.includes('index.html')) return 'index.html';
        return S.files.find(f => /^(html|htm)$/.test(ext(f))) || null;
    }
    function refreshPreview() {
        const fr = $('o2c-frame');
        if (!fr) return;
        const entry = entryFile();
        const lbl = $('o2c-entry');
        const con = $('o2c-console');
        if (con) con.innerHTML = '';
        if (!entry) {
            fr.srcdoc = '<body style="font-family:system-ui;color:#6b7280;padding:24px">No HTML file in this project yet. Add one with New file.</body>';
            if (lbl) lbl.textContent = '';
            return;
        }
        if (lbl) lbl.textContent = entry;
        fr.srcdoc = buildPage(entry, false);
    }
    function logLine(kind, msg) {
        const con = $('o2c-console');
        if (!con) return;
        const d = document.createElement('div');
        d.className = 'px-2 py-0.5 border-b border-white/5 whitespace-pre-wrap break-all';
        d.style.color = kind === 'error' ? '#fca5a5' : kind === 'warn' ? '#fcd34d' : '#cbd5e1';
        d.textContent = (kind === 'log' || kind === 'info' ? '› ' : kind + ': ') + msg;
        con.appendChild(d);
        while (con.children.length > 200) con.removeChild(con.firstChild);
        con.scrollTop = con.scrollHeight;
    }
    window.addEventListener('message', (e) => {
        const fr = $('o2c-frame');
        if (!fr || e.source !== fr.contentWindow || !e.data || !e.data.o2canvas) return;
        const t = e.data.o2canvas, msg = String(e.data.msg || '').slice(0, 2000);
        if (t === 'nav') {
            const f = projFile(msg);
            if (f && /^(html|htm)$/.test(ext(f))) { S.previewEntry = f; refreshPreview(); status('Preview went to ' + f + '.'); }
            else status('The preview only follows links to HTML files in this project (' + msg + ').');
            return;
        }
        logLine(t, msg);
    });

    // ── Rendering ─────────────────────────────────────────────────────────────────────────
    function renderProjects() {
        const box = $('o2c-projects');
        if (!box) return;
        if (!S.projects.length) { box.innerHTML = '<div class="px-3 py-2 text-gray-500 text-xs">No projects yet.</div>'; return; }
        box.innerHTML = S.projects.map(p => `<button data-proj="${esc(p)}" class="w-full text-left px-3 py-1.5 text-xs truncate hover:bg-white/5 ${p === S.project ? 'bg-indigo-500/20 text-indigo-200' : 'text-gray-300'}"><i class="fas fa-folder mr-1.5 text-yellow-500/80"></i>${esc(p)}</button>`).join('');
    }
    function renderFiles() {
        const box = $('o2c-files');
        if (!box) return;
        if (!S.project) { box.innerHTML = '<div class="px-3 py-2 text-gray-500 text-xs">Open or create a project.</div>'; return; }
        if (!S.files.length) { box.innerHTML = '<div class="px-3 py-2 text-gray-500 text-xs">No files. Use New file.</div>'; return; }
        const icon = (f) => ({html: 'fab fa-html5 text-orange-400', htm: 'fab fa-html5 text-orange-400', css: 'fab fa-css3-alt text-sky-400', js: 'fab fa-js text-yellow-300', mjs: 'fab fa-js text-yellow-300', json: 'fas fa-brackets-curly text-lime-300', md: 'fab fa-markdown text-gray-300', svg: 'fas fa-bezier-curve text-pink-300'}[ext(f)] || 'fas fa-file text-gray-400');
        box.innerHTML = S.files.map(f => `<div data-file="${esc(f)}" class="group flex items-center px-3 py-1.5 text-xs cursor-pointer hover:bg-white/5 ${f === S.file ? 'bg-white/10 text-white' : 'text-gray-300'}">
            <i class="${icon(f)} w-4 mr-1.5"></i><span class="flex-1 truncate">${esc(f)}</span>
            ${dirty(f) ? '<span title="Unsaved changes" class="w-1.5 h-1.5 rounded-full bg-amber-400 mr-1"></span>' : ''}
            <button data-fact="rename" data-f="${esc(f)}" title="Rename" class="hidden group-hover:inline px-1 text-gray-400 hover:text-white"><i class="fas fa-i-cursor"></i></button>
            <button data-fact="delete" data-f="${esc(f)}" title="Delete" class="hidden group-hover:inline px-1 text-gray-400 hover:text-red-400"><i class="fas fa-trash"></i></button></div>`).join('');
    }
    function renderTab() {
        const t = $('o2c-tab');
        if (!t) return;
        t.innerHTML = S.file
            ? `<span class="text-gray-200">${esc(S.project)} / <b>${esc(S.file)}</b></span>${dirty(S.file) ? '<span class="ml-2 text-amber-300">unsaved</span>' : '<span class="ml-2 text-gray-500">saved</span>'}`
            : '<span class="text-gray-500">No file open</span>';
        const u = $('o2c-ai-undo');
        if (u) u.classList.toggle('hidden', !(S.aiUndo && S.aiUndo.project === S.project && S.files.includes(S.aiUndo.file)));
    }
    function applyView() {
        const code = $('o2c-code'), prev = $('o2c-prev');
        if (!code || !prev) return;
        code.style.display = S.view === 'preview' ? 'none' : 'flex';
        prev.style.display = S.view === 'code' ? 'none' : 'flex';
        document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('bg-indigo-600', b.dataset.view === S.view));
        if (S.cm) setTimeout(() => S.cm.refresh(), 0);
    }

    // ── Projects and files ────────────────────────────────────────────────────────────────
    async function loadProjects() {
        try {
            const items = await davList(ROOT);
            S.projects = items.filter(i => i.isDir).map(i => i.name.replace(/\/$/, '')).filter(Boolean).sort((a, b) => a.localeCompare(b));
        } catch (e) {
            if (is404(e)) {
                try { await davMkdir(ROOT); } catch (e2) { status('Could not create the canvas folder: ' + e2.message, 'err'); }
                S.projects = [];
            } else { status('One2lvOS Files is not reachable: ' + e.message, 'err'); S.projects = []; renderProjects(); return false; }
        }
        renderProjects();
        return true;
    }
    async function openProject(name) {
        if (S.busy) return;
        S.busy = true;
        status('Opening ' + name + '…');
        try {
            const items = await davList(ROOT + '/' + name);
            const big = items.filter(i => !i.isDir && isText(i.name) && i.size > MAX_BYTES).map(i => i.name);
            const files = items.filter(i => !i.isDir && isText(i.name) && !(i.size > MAX_BYTES)).map(i => i.name)
                .sort((a, b) => (a === 'index.html' ? -1 : b === 'index.html' ? 1 : a.localeCompare(b)));
            const texts = await Promise.all(files.map(f => davRead(fpath(f, name))));
            S.project = name; S.files = files; S.buf = {}; S.saved = {}; S.docs = {}; S.file = null; S.previewEntry = null;
            let restored = 0;
            files.forEach((f, i) => {
                S.saved[f] = texts[i];
                const d = draftGet(f);
                if (d != null && d !== texts[i]) { S.buf[f] = d; restored++; } else { S.buf[f] = texts[i]; if (d != null) draftDel(f); }
            });
            try { localStorage.setItem(LS + 'last', name); } catch (e) {}
            renderProjects();
            openFile(files.includes('index.html') ? 'index.html' : files[0] || null);
            refreshPreview();
            let msg = 'Opened ' + name + ' (' + files.length + ' file' + (files.length === 1 ? '' : 's') + ').';
            if (restored) msg += ' Restored unsaved changes to ' + restored + ' file' + (restored === 1 ? '' : 's') + ' from this device.';
            if (big.length) msg += ' Skipped files over 2 MB: ' + big.join(', ') + '.';
            status(msg, 'ok');
        } catch (e) {
            status('Could not open ' + name + ': ' + e.message, 'err');
        } finally { S.busy = false; }
    }
    function openFile(f) {
        S.file = f;
        if (f) editorShow(f);
        else if (S.cm) { S.cm.swapDoc(window.CodeMirror.Doc('', null)); S.cm.setOption('readOnly', 'nocursor'); }
        else if (S.ta) { S.ta.value = ''; S.ta.disabled = true; }
        if (f && /^(html|htm)$/.test(ext(f))) { S.previewEntry = null; refreshPreview(); }
        renderFiles(); renderTab();
    }
    async function saveFile(f) {
        if (!S.project || !f) return false;
        const text = S.buf[f];
        if (new Blob([text]).size > MAX_BYTES) { status(f + ' is over 2 MB and was not saved.', 'err'); return false; }
        try {
            await davWrite(fpath(f), text);
            S.saved[f] = text;
            if (!dirty(f)) draftDel(f);
            renderFiles(); renderTab();
            status('Saved ' + f + ' to One2lvOS Files at ' + now() + '.', 'ok');
            return true;
        } catch (e) { status('Save failed for ' + f + ': ' + e.message + '. Your edits are kept on this device.', 'err'); return false; }
    }
    async function saveAll() {
        const list = S.files.filter(dirty);
        if (!list.length) { status('Nothing to save.'); return; }
        let ok = 0;
        for (const f of list) if (await saveFile(f)) ok++;
        if (ok === list.length) status('Saved ' + ok + ' file' + (ok === 1 ? '' : 's') + ' to One2lvOS Files at ' + now() + '.', 'ok');
    }
    function validName(n, fileMode) {
        if (!NAME_RE.test(n) || n.includes('..') || /\s$/.test(n)) return 'Use letters, numbers, dots, dashes, underscores or spaces (up to 64), starting with a letter or number.';
        if (fileMode && !isText(n)) return 'Use one of these file types: ' + TEXT_EXT.map(e => '.' + e).join(' ');
        return null;
    }
    async function newProject() {
        const name = (prompt('Name for the new project:', 'my-page') || '').trim();
        if (!name) return;
        const bad = validName(name, false);
        if (bad) { status(bad, 'err'); return; }
        if (S.projects.includes(name)) { status('A project called ' + name + ' already exists.', 'err'); return; }
        status('Creating ' + name + '…');
        try {
            await davMkdir(ROOT + '/' + name);
            const files = starter(name);
            for (const f of Object.keys(files)) await davWrite(fpath(f, name), files[f]);
            await loadProjects();
            await openProject(name);
        } catch (e) { status('Could not create the project: ' + e.message, 'err'); }
    }
    async function newFile() {
        if (!S.project) { status('Open or create a project first.', 'err'); return; }
        const name = (prompt('New file name (for example about.html, theme.css, app.js):') || '').trim();
        if (!name) return;
        const bad = validName(name, true);
        if (bad) { status(bad, 'err'); return; }
        if (S.files.includes(name)) { status(name + ' already exists.', 'err'); return; }
        const text = blankFor(name);
        try {
            await davWrite(fpath(name), text);
            S.files.push(name); S.files.sort((a, b) => (a === 'index.html' ? -1 : b === 'index.html' ? 1 : a.localeCompare(b)));
            S.buf[name] = text; S.saved[name] = text;
            openFile(name);
            status('Created ' + name + '.', 'ok');
        } catch (e) { status('Could not create ' + name + ': ' + e.message, 'err'); }
    }
    async function renameFile(f) {
        const name = (prompt('Rename ' + f + ' to:', f) || '').trim();
        if (!name || name === f) return;
        const bad = validName(name, true);
        if (bad) { status(bad, 'err'); return; }
        if (S.files.includes(name)) { status(name + ' already exists.', 'err'); return; }
        try {
            await davMove(fpath(f), fpath(name));
            S.files[S.files.indexOf(f)] = name;
            S.buf[name] = S.buf[f]; S.saved[name] = S.saved[f]; delete S.buf[f]; delete S.saved[f]; delete S.docs[f];
            const d = draftGet(f); draftDel(f); if (d != null) draftSet(name, d);
            if (S.file === f) openFile(name); else renderFiles();
            refreshPreview();
            status('Renamed ' + f + ' to ' + name + '. Links to the old name in your pages are not changed.', 'ok');
        } catch (e) { status('Rename failed: ' + e.message, 'err'); }
    }
    async function deleteFile(f) {
        if (!confirm('Delete ' + f + ' from ' + S.project + '? This removes it from One2lvOS Files.')) return;
        try {
            await davDelete(fpath(f));
            S.files = S.files.filter(x => x !== f);
            delete S.buf[f]; delete S.saved[f]; delete S.docs[f]; draftDel(f);
            if (S.file === f) openFile(S.files[0] || null); else renderFiles();
            refreshPreview();
            status('Deleted ' + f + '.', 'ok');
        } catch (e) { status('Delete failed: ' + e.message, 'err'); }
    }
    async function importFiles(input) {
        const files = Array.from(input.files || []);
        input.value = '';
        if (!S.project) { status('Open or create a project first.', 'err'); return; }
        for (const file of files) {
            const name = file.name;
            const bad = validName(name, true);
            if (bad) { status(name + ': ' + bad, 'err'); continue; }
            if (file.size > MAX_BYTES) { status(name + ' is over 2 MB.', 'err'); continue; }
            if (S.files.includes(name) && !confirm(name + ' already exists. Replace it?')) continue;
            const text = await file.text();
            try {
                await davWrite(fpath(name), text);
                if (!S.files.includes(name)) S.files.push(name);
                S.buf[name] = text; S.saved[name] = text; delete S.docs[name]; draftDel(name);
                openFile(name);
                status('Imported ' + name + '.', 'ok');
            } catch (e) { status('Import of ' + name + ' failed: ' + e.message, 'err'); }
        }
        refreshPreview();
    }
    function download(name, text, type) {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([text], {type: type || 'text/plain'}));
        a.download = name;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    }
    function downloadPage() {
        const entry = entryFile();
        if (!entry) { status('There is no HTML file to download.', 'err'); return; }
        const base = entry === 'index.html' ? S.project : entry.replace(/\.[^.]+$/, '');
        download(base + '.html', buildPage(entry, true), 'text/html');
        status('Downloaded ' + base + '.html with its CSS and JS built in.', 'ok');
    }

    // ── AI helper (Lumenis's NVIDIA model on the reactor) ───────────────────────────────
    function toggleAI() {
        const p = $('o2c-ai');
        if (!p) return;
        p.classList.toggle('hidden');
        if (!p.classList.contains('hidden')) $('o2c-ai-text').focus();
    }
    function extractCode(reply) {
        const blocks = [...String(reply).matchAll(/```[a-zA-Z0-9_-]*\n([\s\S]*?)```/g)].map(m => m[1]);
        if (blocks.length) return blocks.sort((a, b) => b.length - a.length)[0];
        const open = String(reply).match(/```[a-zA-Z0-9_-]*\n([\s\S]*)$/);
        if (open) return open[1];
        return String(reply).trim() + '\n';
    }
    async function askAI() {
        if (!S.file) { status('Open a file first.', 'err'); return; }
        const ask = ($('o2c-ai-text').value || '').trim();
        if (!ask) { status('Type what you want changed or built.', 'err'); return; }
        const f = S.file, proj = S.project, current = S.buf[f] || '';
        if (current.length > AI_MAX_CHARS) { status(f + ' is too long for the AI helper (over ' + AI_MAX_CHARS.toLocaleString() + ' characters).', 'err'); return; }
        const btn = $('o2c-ai-go');
        btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Working…';
        $('o2c-ai-note').textContent = 'Asking the model. This usually takes 15 to 60 seconds, longer while Lumenis is busy.';
        const prompt = 'You are editing the file "' + f + '" in a small static web project. The project files are: ' + S.files.join(', ') + '.\n' +
            'Instruction: ' + ask + '\n\n' +
            (current.trim() ? 'Current content of ' + f + ':\n```\n' + current + '\n```\n\n' : 'The file is currently empty.\n\n') +
            'Reply with only the complete new content of ' + f + ' in one fenced code block. No explanation. Keep it short enough to finish.';
        try {
            const r = await fetch(AI_URL, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt}), signal: AbortSignal.timeout(180000)});
            const ct = r.headers.get('content-type') || '';
            if (!ct.includes('json')) throw new Error(r.url.includes('cloudflareaccess.com') ? 'Cloudflare sign-in expired: reload the page' : 'HTTP ' + r.status);
            const d = await r.json();
            if (!r.ok || d.error) throw new Error(d.error || ('HTTP ' + r.status));
            if (!d.reply || !String(d.reply).trim()) throw new Error('the model returned an empty reply');
            if (S.project !== proj || !S.files.includes(f)) throw new Error('the project changed while waiting, so nothing was applied');
            const code = extractCode(d.reply);
            if (S.file !== f) openFile(f);
            S.aiUndo = {project: proj, file: f, text: current};
            editorReplace(code);
            let note = 'Applied to ' + f + ' (not saved yet). Answered by ' + (d.model || 'the model') + (d.provider ? ' on ' + d.provider : '') + '.';
            if (/^(html|htm)$/.test(ext(f)) && /<html/i.test(code) && !/<\/html>/i.test(code)) note += ' The reply looks cut off (no closing </html>); replies are limited to about 1024 tokens.';
            $('o2c-ai-note').textContent = note;
            status('AI change applied to ' + f + '. Review it, then Save or Undo AI change.', 'ok');
            refreshPreview();
        } catch (e) {
            $('o2c-ai-note').textContent = 'No change made: ' + e.message;
            status('AI helper failed: ' + e.message, 'err');
        } finally {
            btn.disabled = false; btn.innerHTML = '<i class="fas fa-wand-magic-sparkles mr-1"></i>Apply to open file';
            renderTab();
        }
    }
    function undoAI() {
        const u = S.aiUndo;
        if (!u || u.project !== S.project || !S.files.includes(u.file)) return;
        if (S.file !== u.file) openFile(u.file);
        editorReplace(u.text);
        S.aiUndo = null;
        renderTab();
        status('Put back ' + u.file + ' as it was before the AI change.', 'ok');
    }

    // ── Window ────────────────────────────────────────────────────────────────────────────
    const btn = 'px-2.5 py-1 rounded-md hover:bg-white/10 text-gray-200 text-xs whitespace-nowrap';
    const content = `<div id="o2c-root" class="h-full flex flex-col bg-[#0b0f17] text-gray-200 text-sm">
      <div class="flex items-center gap-1 px-2 py-1.5 border-b border-white/10 bg-[#0f1520] flex-wrap">
        <button data-act="save" class="${btn}" title="Save the open file (Ctrl+S)"><i class="fas fa-save mr-1"></i>Save</button>
        <button data-act="saveall" class="${btn}" title="Save every changed file"><i class="fas fa-layer-group mr-1"></i>Save all</button>
        <button data-act="run" class="${btn}" title="Reload the preview"><i class="fas fa-play mr-1 text-emerald-400"></i>Run</button>
        <span class="w-px h-5 bg-white/10 mx-1"></span>
        <button data-view="code" class="${btn}">Code</button>
        <button data-view="split" class="${btn}">Split</button>
        <button data-view="preview" class="${btn}">Preview</button>
        <span class="w-px h-5 bg-white/10 mx-1"></span>
        <button data-act="dlpage" class="${btn}" title="Download the page as one HTML file with its CSS and JS built in"><i class="fas fa-file-export mr-1"></i>Download page</button>
        <button data-act="dlfile" class="${btn}" title="Download the open file"><i class="fas fa-download mr-1"></i>File</button>
        <button data-act="ai" class="${btn} ml-auto" title="Ask an AI model to write or change the open file"><i class="fas fa-wand-magic-sparkles mr-1 text-fuchsia-300"></i>Ask AI</button>
      </div>
      <div class="flex-1 flex min-h-0">
        <aside class="w-44 shrink-0 border-r border-white/10 bg-[#0d121b] flex flex-col min-h-0">
          <div class="flex items-center justify-between px-3 pt-2 pb-1 text-[10px] uppercase tracking-wider text-gray-500">Projects
            <span><button data-act="refresh" title="Refresh" class="px-1 hover:text-white"><i class="fas fa-sync-alt"></i></button><button data-act="newproj" title="New project" class="px-1 hover:text-white"><i class="fas fa-plus"></i></button></span></div>
          <div id="o2c-projects" class="overflow-auto max-h-40"></div>
          <div class="flex items-center justify-between px-3 pt-3 pb-1 text-[10px] uppercase tracking-wider text-gray-500 border-t border-white/5 mt-1">Files
            <span><label title="Import files from this device" class="px-1 hover:text-white cursor-pointer"><i class="fas fa-file-import"></i><input id="o2c-import" type="file" multiple class="hidden" accept="${TEXT_EXT.map(e => '.' + e).join(',')}"></label><button data-act="newfile" title="New file" class="px-1 hover:text-white"><i class="fas fa-plus"></i></button></span></div>
          <div id="o2c-files" class="flex-1 overflow-auto"></div>
          <div class="px-3 py-2 text-[10px] leading-snug text-gray-500 border-t border-white/5">Saved on this server in One2lvOS Files, folder /canvas. One2lvOS's own workspace, not Google's Gemini Canvas.</div>
        </aside>
        <section id="o2c-code" class="flex-1 min-w-0 flex flex-col">
          <div id="o2c-tab" class="px-3 py-1 text-xs border-b border-white/10 bg-[#111827] truncate"></div>
          <div id="o2c-editor" class="flex-1 min-h-0 relative overflow-hidden"><div class="p-4 text-gray-500 text-xs"><i class="fas fa-spinner fa-spin mr-1"></i>Loading editor…</div></div>
        </section>
        <section id="o2c-prev" class="flex-1 min-w-0 flex flex-col border-l border-white/10">
          <div class="flex items-center gap-2 px-3 py-1 text-xs border-b border-white/10 bg-[#111827]">
            <span class="text-gray-400">Preview</span><span id="o2c-entry" class="text-gray-200 truncate"></span>
            <label class="ml-auto flex items-center gap-1 text-gray-400 cursor-pointer"><input id="o2c-auto" type="checkbox" checked class="accent-indigo-500">Live</label>
            <button data-act="run" title="Reload the preview" class="px-1 text-gray-400 hover:text-white"><i class="fas fa-redo"></i></button></div>
          <iframe id="o2c-frame" title="Page preview" sandbox="allow-scripts allow-forms allow-modals allow-popups" class="flex-1 w-full bg-white border-0"></iframe>
          <div class="flex items-center px-3 py-0.5 text-[10px] uppercase tracking-wider text-gray-500 border-t border-white/10 bg-[#0d121b]">Console<button data-act="clearcon" class="ml-auto normal-case tracking-normal hover:text-white">Clear</button></div>
          <div id="o2c-console" class="h-20 overflow-auto font-mono text-[11px] bg-[#0b0f17]"></div>
        </section>
      </div>
      <div id="o2c-ai" class="hidden border-t border-white/10 bg-[#0f1520] p-2">
        <div class="flex gap-2">
          <textarea id="o2c-ai-text" rows="2" class="flex-1 bg-black/40 border border-white/10 rounded-md px-2 py-1 text-xs outline-none resize-none" placeholder="Describe what to build or change in the open file, for example: add a contact form with name, email and message"></textarea>
          <div class="flex flex-col gap-1">
            <button id="o2c-ai-go" data-act="aigo" class="px-3 py-1 rounded-md bg-fuchsia-700 hover:bg-fuchsia-600 text-white text-xs whitespace-nowrap"><i class="fas fa-wand-magic-sparkles mr-1"></i>Apply to open file</button>
            <button id="o2c-ai-undo" data-act="aiundo" class="hidden px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 text-xs whitespace-nowrap"><i class="fas fa-undo mr-1"></i>Undo AI change</button>
          </div>
        </div>
        <div id="o2c-ai-note" class="text-[11px] text-gray-400 mt-1">Uses Lumenis's NVIDIA model on this server (not Gemini). It rewrites the open file; nothing is saved until you press Save.</div>
      </div>
      <div id="o2c-status" class="px-3 py-1 text-[11px] border-t border-white/10 bg-[#0d121b] truncate" style="color:#9ca3af">Starting…</div>
    </div>`;

    async function init() {
        const root = $('o2c-root');
        if (!root) return;
        root.addEventListener('click', (e) => {
            const v = e.target.closest('[data-view]');
            if (v) { S.view = v.dataset.view; applyView(); if (S.view !== 'code') refreshPreview(); return; }
            const fa = e.target.closest('[data-fact]');
            if (fa) { e.stopPropagation(); if (fa.dataset.fact === 'rename') renameFile(fa.dataset.f); else deleteFile(fa.dataset.f); return; }
            const fl = e.target.closest('[data-file]');
            if (fl && fl.closest('#o2c-files')) { openFile(fl.dataset.file); return; }
            const pj = e.target.closest('[data-proj]');
            if (pj) { if (pj.dataset.proj !== S.project) openProject(pj.dataset.proj); return; }
            const a = e.target.closest('[data-act]');
            if (!a) return;
            const act = a.dataset.act;
            if (act === 'save') saveFile(S.file);
            else if (act === 'saveall') saveAll();
            else if (act === 'run') { S.previewEntry = null; refreshPreview(); }
            else if (act === 'dlpage') downloadPage();
            else if (act === 'dlfile') { if (S.file) download(S.file, S.buf[S.file] || ''); }
            else if (act === 'ai') toggleAI();
            else if (act === 'aigo') askAI();
            else if (act === 'aiundo') undoAI();
            else if (act === 'newproj') newProject();
            else if (act === 'newfile') newFile();
            else if (act === 'refresh') loadProjects();
            else if (act === 'clearcon') { const c = $('o2c-console'); if (c) c.innerHTML = ''; }
        });
        $('o2c-import').addEventListener('change', (e) => importFiles(e.target));
        $('o2c-auto').checked = S.auto;
        $('o2c-auto').addEventListener('change', (e) => { S.auto = e.target.checked; if (S.auto) refreshPreview(); });
        $('o2c-ai-text').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) askAI(); });
        applyView();
        await setupEditor();
        renderTab(); renderFiles();
        if (!(await loadProjects())) return;
        // Reopen the same project, keeping edits not yet saved, or the last one used.
        if (S.project && S.projects.includes(S.project) && S.files.length) {
            renderProjects(); openFile(S.file || S.files[0]); refreshPreview();
            status('Reopened ' + S.project + '.', 'ok');
            return;
        }
        let last = null;
        try { last = localStorage.getItem(LS + 'last'); } catch (e) {}
        const pick = S.projects.includes(last) ? last : S.projects[0];
        if (pick) await openProject(pick);
        else { renderFiles(); refreshPreview(); status('No projects yet. Press + next to Projects to start one.'); }
    }

    window.addEventListener('beforeunload', (e) => {
        if (S.project && anyDirty()) { e.preventDefault(); e.returnValue = ''; }
    });

    const W = Math.max(360, Math.min(1180, (window.innerWidth || 1200) - 24));
    const H = Math.max(420, Math.min(720, (window.innerHeight || 800) - 90));
    if (typeof apps === 'object') {
        apps['canvas'] = {
            name: 'Canvas', icon: 'fas fa-code', color: 'text-indigo-300', width: W, height: H, content,
            // The old window lingers 200 ms after a close, so wait for it to go before wiring the new one.
            onOpen: () => setTimeout(init, 260),
            onClose: () => {
                clearTimeout(S.draftTimer);
                if (S.project) S.files.forEach(f => { if (dirty(f)) draftSet(f, S.buf[f]); });
                S.cm = null; S.ta = null; S.docs = {};
            }
        };
    }
    window.O2Canvas = {state: S, refreshPreview, buildPage};
})();
