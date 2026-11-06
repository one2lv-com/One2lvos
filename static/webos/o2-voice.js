/* One2lvOS voice layer — speech input, spoken replies and live conversation for Lumenis Chat.
 *
 * Engines, picked by what this device really supports (checked at runtime, never assumed):
 *   Speech to text : Gemini via the reactor proxy (/api/voice, key stays on the server)
 *                    Gemini direct with a key saved on this device (o2_gemini_key, localStorage)
 *                    Android native SpeechRecognizer (window.O2NativeSpeech bridge, APK only)
 *                    Browser Web Speech recognition (Chrome/Edge desktop; not in Android WebView)
 *   Text to speech : Gemini TTS (proxy or device key), Android native TextToSpeech, browser speechSynthesis
 * Models: gemini-4-argon (audio in, text out) for transcription, gemini-3.8-flash-tts for speech.
 *
 * Feedback guard: strictly half-duplex. The mic is closed while Lumenis speaks and reopens only after
 * playback ends plus a cooldown; capture asks for echo cancellation; and a transcript that matches what
 * was just spoken is dropped instead of being sent back to Lumenis.
 *
 * It talks to the chat only through the chat's own functions (lcSend, lcAddMsg, lcSetDot), so the
 * hosted desktop (reactor WebSocket) and the APK (direct NVIDIA) both keep their own send path.
 */
(function () {
  'use strict';
  if (window.O2Voice) return;

  var API = 'https://generativelanguage.googleapis.com/v1beta/interactions';
  var CFG_KEY = 'o2_voice_cfg_v1';
  var GKEY = 'o2_gemini_key';
  var DEFAULTS = {
    stt: 'auto', tts: 'auto', speakReplies: false, muted: false,
    voice: 'Kore', lang: (navigator.language || 'en-US'),
    sttModel: 'gemini-4-argon', ttsModel: 'gemini-3.8-flash-tts'
  };
  var TRANSCRIBE_PROMPT = 'Transcribe the speech in this audio exactly as spoken, in the language spoken. ' +
    'Output only the transcript text, with no labels, quotes or commentary. If there is no intelligible speech, output nothing.';

  function loadCfg() {
    var c = {};
    try { c = JSON.parse(localStorage.getItem(CFG_KEY) || '{}') || {}; } catch (_) { c = {}; }
    var out = {};
    Object.keys(DEFAULTS).forEach(function (k) { out[k] = (c[k] === undefined ? DEFAULTS[k] : c[k]); });
    return out;
  }
  var cfg = loadCfg();
  function saveCfg() { try { localStorage.setItem(CFG_KEY, JSON.stringify(cfg)); } catch (_) {} }
  function deviceKey() { try { return (localStorage.getItem(GKEY) || '').trim(); } catch (_) { return ''; } }

  var isApk = !!(window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform());
  var native = window.O2NativeSpeech || null;
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;

  // ── capability detection ──
  var caps = {
    secure: !!window.isSecureContext,
    mic: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    recorder: typeof window.MediaRecorder === 'function',
    browserStt: !!SR && !isApk,           // WebView exposes no working recognizer
    browserTts: false, browserVoices: 0,
    nativeStt: false, nativeTts: false,
    proxy: false, proxyChecked: false, proxyModels: null
  };
  function refreshNative() {          // the bridge can appear after this script runs; look again when needed
    if (!native && window.O2NativeSpeech) native = window.O2NativeSpeech;
    try { caps.nativeStt = !!(native && native.sttAvailable && native.sttAvailable()); } catch (_) { caps.nativeStt = false; }
    try { caps.nativeTts = !!(native && native.ttsAvailable && native.ttsAvailable()); } catch (_) { caps.nativeTts = false; }
  }
  refreshNative();
  function refreshVoices() {
    try {
      var v = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
      caps.browserVoices = v.length; caps.browserTts = v.length > 0;
    } catch (_) {}
  }
  refreshVoices();
  if (window.speechSynthesis && 'onvoiceschanged' in window.speechSynthesis) {
    window.speechSynthesis.addEventListener('voiceschanged', function () { refreshVoices(); renderStatus(); });
  }
  function checkProxy() {
    if (isApk || !/^https?:$/.test(location.protocol)) { caps.proxyChecked = true; return Promise.resolve(false); }
    return fetch('/api/voice/status', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
      .then(function (r) {
        var ct = r.headers.get('content-type') || '';
        if (!r.ok || ct.indexOf('json') < 0) return null;
        return r.json();
      })
      .then(function (d) {
        caps.proxy = !!(d && typeof d.gemini === 'boolean' && d.gemini);
        caps.proxyModels = d && d.stt_model ? { stt: d.stt_model, tts: d.tts_model } : null;
        caps.proxyChecked = true; renderStatus(); return caps.proxy;
      })
      .catch(function () { caps.proxyChecked = true; caps.proxy = false; return false; });
  }
  var proxyReady = checkProxy();

  function sttEngine() {
    if (!native) refreshNative();
    var canRec = caps.mic && caps.recorder;
    var order = { auto: ['gproxy', 'gkey', 'native', 'browser'], gemini: ['gproxy', 'gkey'], native: ['native'], browser: ['browser'] }[cfg.stt] || ['gproxy', 'gkey', 'native', 'browser'];
    for (var i = 0; i < order.length; i++) {
      var e = order[i];
      if (e === 'gproxy' && caps.proxy && canRec) return e;
      if (e === 'gkey' && deviceKey() && canRec) return e;
      if (e === 'native' && caps.nativeStt) return e;
      if (e === 'browser' && caps.browserStt) return e;
    }
    return null;
  }
  function ttsOrder() {
    if (!native) refreshNative();
    var order = { auto: ['gproxy', 'gkey', 'native', 'browser'], gemini: ['gproxy', 'gkey'], native: ['native'], browser: ['browser'] }[cfg.tts] || ['gproxy', 'gkey', 'native', 'browser'];
    return order.filter(function (e) {
      return (e === 'gproxy' && caps.proxy) || (e === 'gkey' && !!deviceKey()) ||
        (e === 'native' && caps.nativeTts) || (e === 'browser' && caps.browserTts);
    });
  }
  var ENGINE_NAMES = { gproxy: 'Gemini (reactor)', gkey: 'Gemini (this device)', native: 'Android speech', browser: 'Browser speech' };

  // ── state ──
  var st = {
    phase: 'idle',          // idle | listening | transcribing | thinking | speaking
    live: false, ptt: false,
    level: 0, error: '', note: '',
    rec: null,              // active capture: {finish(keep)}
    audio: null,            // active <audio>
    speakingUntil: 0, lastSpoken: '', lastSpokenAt: 0,
    turn: null,             // pending chat turn {resolve, reject, timer}
    emptyRuns: 0, gen: 0
  };
  function setPhase(p, note) { st.phase = p; if (note !== undefined) st.note = note; renderStatus(); }
  function sys(msg) { try { if (typeof window.lcAddMsg === 'function') window.lcAddMsg('sys', msg); } catch (_) {} }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  // ── errors ──
  function micError(e) {
    var n = (e && e.name) || '';
    if (n === 'NotAllowedError' || n === 'PermissionDeniedError' || n === 'SecurityError')
      return isApk ? 'Microphone permission denied. Allow it in Android Settings > Apps > One2lvOS > Permissions, then try again.'
                   : 'Microphone permission denied. Allow the microphone for this site in the browser, then try again.';
    if (n === 'NotFoundError' || n === 'DevicesNotFoundError') return 'No microphone was found on this device.';
    if (n === 'NotReadableError' || n === 'TrackStartError') return 'The microphone is busy in another app.';
    if (!caps.secure) return 'The microphone needs a secure (https) page.';
    return 'Microphone error: ' + ((e && e.message) || n || e);
  }
  function geminiError(status, body) {
    var msg = '';
    try { var d = JSON.parse(body); msg = (d.error && (d.error.message || d.error)) || d.detail || ''; } catch (_) { msg = String(body || '').slice(0, 160); }
    if (status === 400 && /api key/i.test(msg)) return 'Gemini rejected the API key.';
    if (status === 401 || status === 403) return 'Gemini refused the key (' + status + '). ' + msg;
    if (status === 404) return 'Gemini model not found (' + status + '). ' + msg;
    if (status === 429) return 'Gemini quota or rate limit reached (429).';
    if (status === 503 && /GEMINI_API_KEY/.test(msg)) return 'The reactor has no GEMINI_API_KEY set.';
    return 'Gemini error ' + status + (msg ? ': ' + msg : '');
  }

  // ── capture with voice-activity endpointing ──
  function pickMime() {
    var list = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    for (var i = 0; i < list.length; i++) { try { if (MediaRecorder.isTypeSupported(list[i])) return list[i]; } catch (_) {} }
    return '';
  }
  function openMic() {
    return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  }
  function recordUtterance(opts) {
    opts = opts || {};
    var silenceMs = opts.silenceMs || 1100, noSpeechMs = opts.noSpeechMs || 8000, maxMs = opts.maxMs || 20000;
    return openMic().then(function (stream) {
      return new Promise(function (resolve) {
        var mime = pickMime();
        var rec, chunks = [], ctx = null, an = null, timer = null, done = false;
        var start = Date.now(), speechAt = 0, lastVoice = 0, voicedMs = 0, floor = 0, floorN = 0, keep = true;
        try { rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream); }
        catch (e) { stream.getTracks().forEach(function (t) { t.stop(); }); resolve({ error: 'Recording is not supported here: ' + e.message }); return; }
        try {
          var AC = window.AudioContext || window.webkitAudioContext;
          ctx = new AC(); an = ctx.createAnalyser(); an.fftSize = 1024;
          ctx.createMediaStreamSource(stream).connect(an);
          if (ctx.state === 'suspended') ctx.resume().catch(function () {});
        } catch (_) { an = null; }
        var buf = an ? new Float32Array(an.fftSize) : null;
        function cleanup() {
          clearInterval(timer);
          stream.getTracks().forEach(function (t) { t.stop(); });
          if (ctx) ctx.close().catch(function () {});
          st.level = 0; renderLevel();
        }
        function finish(k) { if (done) return; done = true; keep = k !== false; try { if (rec.state !== 'inactive') rec.stop(); else onStop(); } catch (_) { onStop(); } }
        function onStop() {
          cleanup();
          st.rec = null;
          var blob = new Blob(chunks, { type: (rec.mimeType || mime || 'audio/webm') });
          var heard = an ? (speechAt > 0 && voicedMs >= 200) : blob.size > 2000;
          if (!keep) return resolve({ cancelled: true });
          if (!heard || !blob.size) return resolve({ empty: true });
          resolve({ blob: blob, mime: blob.type });
        }
        rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        rec.onstop = onStop;
        rec.start(250);
        st.rec = { finish: finish };
        timer = setInterval(function () {
          var now = Date.now(), el = now - start;
          if (an) {
            an.getFloatTimeDomainData(buf);
            var s = 0; for (var i = 0; i < buf.length; i++) s += buf[i] * buf[i];
            var rms = Math.sqrt(s / buf.length);
            if (el < 300) { floor = (floor * floorN + rms) / (floorN + 1); floorN++; }
            var thr = Math.max(0.012, floor * 2.5);
            st.level = Math.min(1, rms / 0.15); renderLevel();
            if (el >= 300 && rms > thr) { if (!speechAt) speechAt = now; voicedMs += 50; lastVoice = now; }
            if (speechAt && now - lastVoice > silenceMs) return finish(true);
            if (!speechAt && el > noSpeechMs) return finish(true);
          }
          if (el > maxMs) finish(true);
        }, 50);
      });
    }, function (e) { return { error: micError(e) }; });
  }

  function blobToB64(blob) {
    return new Promise(function (res, rej) {
      var r = new FileReader();
      r.onload = function () { res(String(r.result).split(',')[1] || ''); };
      r.onerror = function () { rej(r.error); };
      r.readAsDataURL(blob);
    });
  }
  function outputs(d, kind) {
    var out = [];
    (d && d.steps || []).forEach(function (s) {
      if (s.type !== 'model_output') return;
      (s.content || []).forEach(function (c) { if (c.type === kind) out.push(c); });
    });
    if (!out.length && kind === 'text' && d && typeof d.output_text === 'string') out.push({ text: d.output_text });
    return out;
  }
  function transcribeGemini(engine, blob) {
    var mime = (blob.type || 'audio/webm').split(';')[0];
    return blobToB64(blob).then(function (b64) {
      if (engine === 'gproxy') {
        return fetch('/api/voice/transcribe', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ audio_b64: b64, mime_type: mime }) })
          .then(function (r) { return r.text().then(function (t) { if (!r.ok) throw new Error(geminiError(r.status, t)); return JSON.parse(t).text || ''; }); });
      }
      return fetch(API, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': deviceKey() },
        body: JSON.stringify({ model: cfg.sttModel, input: [{ type: 'text', text: TRANSCRIBE_PROMPT }, { type: 'audio', data: b64, mime_type: mime }], generation_config: { thinking_level: 'low', max_output_tokens: 2048 } })
      }).then(function (r) { return r.text().then(function (t) { if (!r.ok) throw new Error(geminiError(r.status, t)); return outputs(JSON.parse(t), 'text').map(function (c) { return c.text || ''; }).join('').trim(); }); });
    });
  }

  // Native Android SpeechRecognizer, events come back through window.__o2SpeechEvent
  var nativeWait = null;
  window.__o2SpeechEvent = function (json) {
    var ev; try { ev = typeof json === 'string' ? JSON.parse(json) : json; } catch (_) { return; }
    if (!ev || !ev.type) return;
    if (ev.type === 'stt-rms') { st.level = Math.max(0, Math.min(1, (ev.value + 2) / 12)); renderLevel(); return; }
    if (ev.type.indexOf('tts-') === 0 && ttsWait && (ev.id === ttsWait.id || !ev.id)) {
      if (ev.type === 'tts-done' || ev.type === 'tts-stopped') { var w = ttsWait; ttsWait = null; w.resolve(); }
      else if (ev.type === 'tts-error') { var w2 = ttsWait; ttsWait = null; w2.reject(new Error('Android speech failed (' + (ev.code || 'error') + ')')); }
      return;
    }
    if (!nativeWait) return;
    if (ev.type === 'stt-partial') { st.note = ev.text || ''; renderStatus(); }
    else if (ev.type === 'stt-result') { var n = nativeWait; nativeWait = null; n.resolve({ text: ev.text || '' }); }
    else if (ev.type === 'stt-error') {
      var n2 = nativeWait; nativeWait = null;
      var code = ev.code;
      if (code === 6 || code === 7) n2.resolve({ empty: true });                  // speech timeout / no match
      else if (code === 9) n2.resolve({ error: 'Microphone permission denied. Allow it in Android Settings > Apps > One2lvOS > Permissions.' });
      else if (code === 2 || code === 1) n2.resolve({ error: 'Android speech recognition needs a network connection (error ' + code + ').' });
      else n2.resolve({ error: 'Android speech recognition error ' + code + (ev.text ? ': ' + ev.text : '') });
    }
  };
  function listenNative() {
    var pre = caps.mic ? openMic().then(function (s) { s.getTracks().forEach(function (t) { t.stop(); }); return null; }, function (e) { return micError(e); }) : Promise.resolve(null);
    return pre.then(function (err) {
      if (err) return { error: err };
      return new Promise(function (resolve) {
        nativeWait = { resolve: resolve };
        st.rec = { finish: function (keep) { try { if (keep === false) { native.cancelListening(); if (nativeWait) { nativeWait = null; resolve({ cancelled: true }); } } else native.stopListening(); } catch (_) {} } };
        try { native.startListening(cfg.lang || ''); } catch (e) { nativeWait = null; resolve({ error: 'Android speech recognition could not start: ' + e.message }); }
      }).then(function (r) { st.rec = null; st.level = 0; renderLevel(); return r; });
    });
  }
  function listenBrowser() {
    return new Promise(function (resolve) {
      var r; try { r = new SR(); } catch (e) { return resolve({ error: 'Speech recognition could not start: ' + e.message }); }
      var final = '', settled = false, cancelled = false;
      r.lang = cfg.lang || 'en-US'; r.interimResults = true; r.continuous = false; r.maxAlternatives = 1;
      r.onresult = function (e) {
        var interim = '';
        for (var i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) final += e.results[i][0].transcript; else interim += e.results[i][0].transcript;
        }
        st.note = (final + ' ' + interim).trim(); renderStatus();
      };
      r.onerror = function (e) {
        if (settled) return; settled = true; st.rec = null;
        if (e.error === 'no-speech' || e.error === 'aborted') return resolve(cancelled ? { cancelled: true } : { empty: true });
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') return resolve({ error: micError({ name: 'NotAllowedError' }) });
        if (e.error === 'network') return resolve({ error: 'Browser speech recognition needs a network connection.' });
        resolve({ error: 'Speech recognition error: ' + e.error });
      };
      r.onend = function () { if (settled) return; settled = true; st.rec = null; resolve(cancelled ? { cancelled: true } : (final.trim() ? { text: final.trim() } : { empty: true })); };
      st.rec = { finish: function (keep) { if (keep === false) { cancelled = true; try { r.abort(); } catch (_) {} } else { try { r.stop(); } catch (_) {} } } };
      try { r.start(); } catch (e) { settled = true; st.rec = null; resolve({ error: 'Speech recognition could not start: ' + e.message }); }
    });
  }

  // One utterance -> text. Never runs while speaking.
  function hear(opts) {
    var engine = sttEngine();
    if (!engine) return Promise.resolve({ error: noSttReason() });
    var wait = Math.max(0, st.speakingUntil - Date.now());
    setPhase('listening', '');
    return sleep(wait).then(function () {
      if (engine === 'native') return listenNative();
      if (engine === 'browser') return listenBrowser();
      return recordUtterance(opts).then(function (r) {
        if (!r.blob) return r;
        setPhase('transcribing', '');
        return transcribeGemini(engine, r.blob).then(function (t) { return t ? { text: t } : { empty: true }; }, function (e) { return { error: e.message }; });
      });
    }).then(function (r) { r.engine = engine; return r; });
  }
  function noSttReason() {
    if (cfg.stt === 'gemini') return (caps.mic && caps.recorder) ? 'Gemini speech needs GEMINI_API_KEY on the reactor or a Gemini key saved on this device (voice settings).' : 'This device cannot record audio for Gemini.';
    if (cfg.stt === 'native') return 'Android speech recognition is not available here.';
    if (cfg.stt === 'browser') return isApk ? 'Android WebView has no browser speech recognition. Use Gemini or Android speech.' : 'This browser has no speech recognition.';
    if (!caps.secure) return 'Speech input needs a secure (https) page.';
    return 'No speech input is available: add a Gemini key in voice settings' + (isApk ? '' : ' or use Chrome/Edge') + '.';
  }

  // ── speaking ──
  var ttsWait = null;
  function cleanForSpeech(t) {
    return String(t || '')
      .replace(/```[\s\S]*?```/g, ' (code omitted) ')
      .replace(/`([^`]*)`/g, '$1')
      .replace(/https?:\/\/\S+/g, 'a link')
      .replace(/[*_#>|~]+/g, ' ')
      .replace(/\s+/g, ' ').trim().slice(0, 2500);
  }
  function playBlob(blob) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(blob);
      var a = new Audio(url); st.audio = a;
      var fin = function (err) { URL.revokeObjectURL(url); if (st.audio === a) st.audio = null; err ? reject(err) : resolve(); };
      a.onended = function () { fin(); };
      a.onerror = function () { fin(new Error('Audio playback failed')); };
      a.onpause = function () { if (!a.ended) fin(); };
      a.play().catch(function (e) { fin(new Error(e.name === 'NotAllowedError' ? 'The browser blocked audio playback. Tap the page once and try again.' : 'Audio playback failed: ' + e.message)); });
    });
  }
  function speakWith(engine, text) {
    if (engine === 'gproxy') {
      return fetch('/api/voice/speak', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text, voice: cfg.voice }) })
        .then(function (r) { if (!r.ok) return r.text().then(function (t) { throw new Error(geminiError(r.status, t)); }); return r.blob(); })
        .then(playBlob);
    }
    if (engine === 'gkey') {
      return fetch(API, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': deviceKey() },
        body: JSON.stringify({ model: cfg.ttsModel, input: [{ type: 'user_input', content: [{ type: 'text', text: text }] }], response_format: { type: 'audio' }, generation_config: { speech_config: [{ voice: cfg.voice || 'Kore' }] } })
      }).then(function (r) { return r.text().then(function (t) { if (!r.ok) throw new Error(geminiError(r.status, t)); return JSON.parse(t); }); })
        .then(function (d) {
          var a = outputs(d, 'audio'); var last = a[a.length - 1];
          if (!last || !last.data) throw new Error('Gemini returned no audio');
          var bin = atob(last.data), u8 = new Uint8Array(bin.length);
          for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
          return playBlob(new Blob([u8], { type: last.mime_type || 'audio/wav' }));
        });
    }
    if (engine === 'native') {
      return new Promise(function (resolve, reject) {
        var id = 'u' + Date.now();
        ttsWait = { id: id, resolve: resolve, reject: reject };
        try { native.speak(text, id, cfg.lang || ''); } catch (e) { ttsWait = null; reject(e); }
      });
    }
    if (engine === 'browser') {
      return new Promise(function (resolve, reject) {
        var u = new SpeechSynthesisUtterance(text); u.lang = cfg.lang || 'en-US';
        u.onend = function () { resolve(); };
        u.onerror = function (e) { e.error === 'interrupted' || e.error === 'canceled' ? resolve() : reject(new Error('Browser speech failed: ' + e.error)); };
        window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
      });
    }
    return Promise.reject(new Error('no engine'));
  }
  function speak(text) {
    text = cleanForSpeech(text);
    if (!text || cfg.muted) return Promise.resolve(false);
    var order = ttsOrder();
    if (!order.length) { sys('Voice: no speech output on this device. Add a Gemini key in voice settings' + (isApk ? '.' : ' or use a browser with speech voices.')); return Promise.resolve(false); }
    abortCapture();                                  // half-duplex: mic closed before we talk
    var my = ++st.gen;
    setPhase('speaking', '');
    st.lastSpoken = text; st.speakingUntil = Date.now() + 600000;
    var i = 0;
    function attempt() {
      var eng = order[i];
      return speakWith(eng, text).catch(function (e) {
        if (my !== st.gen) return;
        i++;
        if (i < order.length && cfg.tts === 'auto') { sys('Voice: ' + ENGINE_NAMES[eng] + ' failed (' + e.message + '), using ' + ENGINE_NAMES[order[i]] + '.'); return attempt(); }
        throw e;
      });
    }
    return attempt().then(function () { return true; }, function (e) { sys('Voice: ' + e.message); return false; })
      .then(function (ok) {
        st.lastSpokenAt = Date.now(); st.speakingUntil = Date.now() + 450;   // cooldown before the mic reopens
        if (my === st.gen && st.phase === 'speaking') setPhase(st.live ? 'listening' : 'idle', '');
        return ok;
      });
  }
  function stopSpeaking() {
    st.gen++;
    if (st.audio) { try { st.audio.pause(); } catch (_) {} st.audio = null; }
    try { if (native && native.stopSpeaking) native.stopSpeaking(); } catch (_) {}
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (_) {}
    if (ttsWait) { var w = ttsWait; ttsWait = null; w.resolve(); }
    st.speakingUntil = Date.now() + 300; st.lastSpokenAt = Date.now();
  }
  function abortCapture() { if (st.rec) { try { st.rec.finish(false); } catch (_) {} st.rec = null; } }

  // Echo guard: drop a transcript that is just Lumenis's own last line coming back through the speaker.
  function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9\u00c0-\uffff ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
  function isEcho(t) {
    if (!st.lastSpoken || Date.now() - st.lastSpokenAt > 8000) return false;
    var a = norm(t), b = norm(st.lastSpoken);
    if (!a) return false;
    if (a.length > 12 && b.indexOf(a) >= 0) return true;
    var wa = a.split(' '), wb = {}; b.split(' ').forEach(function (w) { wb[w] = 1; });
    if (wa.length < 4) return false;
    var hit = wa.filter(function (w) { return wb[w]; }).length;
    return hit / wa.length >= 0.8;
  }

  // ── chat bridge ──
  var hook = { busy: false, aiEl: null, userSeen: false, sysMsg: '', wrapped: false };
  function wrapChat() {
    if (typeof window.lcAddMsg === 'function' && !window.lcAddMsg.__o2v) {
      var add = window.lcAddMsg;
      var w = function (role, text) {
        var el = add.apply(this, arguments);
        if (role === 'ai') hook.aiEl = el;
        else if (role === 'user') hook.userSeen = true;
        else if (role === 'sys') hook.sysMsg = String(text || '');
        return el;
      };
      w.__o2v = true; window.lcAddMsg = w;
    }
    if (typeof window.lcSetDot === 'function' && !window.lcSetDot.__o2v) {
      var dot = window.lcSetDot;
      var d = function (state) {
        var r = dot.apply(this, arguments);
        if (state === 'busy') { hook.busy = true; hook.aiEl = null; }
        else if (hook.busy) { hook.busy = false; replyDone(state); }
        return r;
      };
      d.__o2v = true; window.lcSetDot = d;
    }
  }
  function replyDone(state) {
    var text = hook.aiEl ? (hook.aiEl.textContent || '').trim() : '';
    var t = st.turn;
    if (t) { st.turn = null; clearTimeout(t.timer); text ? t.resolve(text) : t.reject(new Error(hook.sysMsg || 'Lumenis did not answer.')); return; }
    if (text && cfg.speakReplies && !st.live) speak(text);       // typed messages, spoken replies
  }
  function askLumenis(text) {
    wrapChat();
    var inp = document.getElementById('lc-inp');
    if (!inp || typeof window.lcSend !== 'function') return Promise.reject(new Error('Open Lumenis Chat first.'));
    return new Promise(function (resolve, reject) {
      hook.userSeen = false; hook.sysMsg = '';
      st.turn = { resolve: resolve, reject: reject, timer: setTimeout(function () { if (st.turn) { st.turn = null; reject(new Error('Lumenis took longer than 5 minutes to answer.')); } }, 300000) };
      inp.value = text;
      var p;
      try { p = window.lcSend(); } catch (e) { clearTimeout(st.turn.timer); st.turn = null; return reject(e); }
      if (!hook.userSeen) {           // the chat refused it (not connected / no key) before sending
        clearTimeout(st.turn.timer); st.turn = null; inp.value = '';
        reject(new Error(hook.sysMsg || 'The chat did not send the message.'));
      }
      if (p && p.then) p.catch(function () {});
    });
  }

  // ── modes ──
  function pushToTalk() {
    if (st.live) return;
    if (st.ptt && st.rec) { st.ptt = false; st.rec.finish(true); return; }    // second tap: send now
    if (st.phase === 'speaking') stopSpeaking();             // tap while Lumenis talks: cut him off and listen
    else if (st.phase !== 'idle') { stopAll(); return; }
    st.ptt = true; st.error = '';
    hear({ silenceMs: 1600, noSpeechMs: 10000, maxMs: 60000 }).then(function (r) {
      st.ptt = false;
      if (r.error) { st.error = r.error; sys('Voice: ' + r.error); setPhase('idle', ''); return; }
      if (!r.text) { setPhase('idle', r.cancelled ? '' : 'Didn\'t catch anything.'); return; }
      setPhase('thinking', '');
      return askLumenis(r.text).then(function (reply) { return cfg.muted ? null : speak(reply); }, function (e) { sys('Voice: ' + e.message); })
        .then(function () { if (!st.live) setPhase('idle', ''); });
    });
  }
  function startLive() {
    if (st.live) return;
    if (!sttEngine()) { st.error = noSttReason(); sys('Voice: ' + st.error); renderStatus(); return; }
    stopSpeaking();
    st.live = true; st.emptyRuns = 0; st.error = '';
    sys('Live conversation on. Talk to Lumenis; tap Stop to end.');
    renderStatus();
    loop();
  }
  function loop() {
    if (!st.live) return;
    hear({ silenceMs: 1100, noSpeechMs: 9000, maxMs: 25000 }).then(function (r) {
      if (!st.live) return;
      if (r.cancelled) return;
      if (r.error) { st.error = r.error; sys('Voice: ' + r.error + ' Live conversation stopped.'); return stopLive(true); }
      if (!r.text) {
        if (++st.emptyRuns >= 3) { sys('Live conversation paused: no speech heard.'); return stopLive(true); }
        return loop();
      }
      if (isEcho(r.text)) { st.note = 'Ignored Lumenis\'s own voice'; renderStatus(); return loop(); }
      st.emptyRuns = 0;
      setPhase('thinking', '');
      return askLumenis(r.text).then(function (reply) {
        if (!st.live) return;
        return speak(reply);
      }, function (e) { sys('Voice: ' + e.message + ' Live conversation stopped.'); stopLive(true); })
        .then(function () { if (st.live) loop(); });
    });
  }
  function stopLive(quiet) {
    if (!st.live) return;
    st.live = false; abortCapture(); stopSpeaking();
    if (st.turn) { clearTimeout(st.turn.timer); st.turn = null; }
    setPhase('idle', '');
    if (!quiet) sys('Live conversation off.');
  }
  function stopAll() {
    st.ptt = false;
    if (st.live) stopLive(false);
    abortCapture(); stopSpeaking();
    if (st.turn) { clearTimeout(st.turn.timer); st.turn = null; }
    setPhase('idle', '');
  }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && st.phase !== 'idle') stopAll(); });
  document.addEventListener('visibilitychange', function () { if (document.hidden && st.phase !== 'idle') stopAll(); });

  // ── UI (injected into the Lumenis Chat window when it opens) ──
  var B = 'border:1px solid rgba(0,240,255,.25);background:rgba(0,0,0,.35);color:#ccd6f6;border-radius:8px;padding:0 11px;height:36px;font-size:.8rem;cursor:pointer;display:inline-flex;align-items:center;gap:6px;flex-shrink:0';
  function el(tag, css, html) { var e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; }
  var ui = null;
  function inject() {
    var inp = document.getElementById('lc-inp');
    if (!inp) { if (ui) { if (st.phase !== 'idle') stopAll(); ui = null; } return; }
    if (document.getElementById('o2v-bar')) return;
    wrapChat();
    var row = inp.parentNode;
    var sendBtn = row.querySelector('button');
    var mic = el('button', B, '<i class="fas fa-microphone"></i>'); mic.id = 'o2v-mic'; mic.title = 'Speak to Lumenis (tap again to send)';
    var live = el('button', B, '<i class="fas fa-headset"></i><span>Live</span>'); live.id = 'o2v-live'; live.title = 'Start a live voice conversation';
    var spk = el('button', B, ''); spk.id = 'o2v-spk';
    var gear = el('button', B, '<i class="fas fa-sliders-h"></i>'); gear.id = 'o2v-gear'; gear.title = 'Voice settings';
    mic.onclick = pushToTalk;
    live.onclick = function () { st.live ? stopLive(false) : startLive(); };
    spk.onclick = function () {
      if (st.phase === 'speaking') { stopSpeaking(); setPhase(st.live ? 'listening' : 'idle', ''); }
      cfg.muted = !cfg.muted; saveCfg(); renderStatus();
    };
    gear.onclick = toggleSettings;
    [mic, live, spk, gear].forEach(function (b) { row.insertBefore(b, sendBtn || null); });
    var bar = el('div', 'display:none;align-items:center;gap:10px;padding:6px 14px;background:#0b0418;border-top:1px solid rgba(0,240,255,.1);font-size:.74rem;color:#8fa3c7;flex-shrink:0');
    bar.id = 'o2v-bar';
    bar.innerHTML = '<span id="o2v-phase" style="color:#00f0ff;font-weight:600;min-width:84px"></span>' +
      '<span style="width:70px;height:6px;border-radius:3px;background:rgba(255,255,255,.08);overflow:hidden;flex-shrink:0"><span id="o2v-lvl" style="display:block;height:100%;width:0;background:linear-gradient(90deg,#00f0ff,#ff00d4);transition:width .08s"></span></span>' +
      '<span id="o2v-note" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"></span>' +
      '<span id="o2v-eng" style="color:#5a6a88"></span>' +
      '<button id="o2v-stop" style="' + B + ';height:26px;border-color:rgba(255,80,120,.5);color:#ff7a9a"><i class="fas fa-stop"></i>Stop</button>';
    row.parentNode.insertBefore(bar, row);
    var panel = el('div', 'display:none;padding:10px 14px;background:#0b0418;border-top:1px solid rgba(0,240,255,.1);font-size:.76rem;color:#ccd6f6;flex-shrink:0;max-height:46%;overflow-y:auto');
    panel.id = 'o2v-panel';
    row.parentNode.insertBefore(panel, bar);
    document.getElementById('o2v-stop').onclick = stopAll;
    ui = true;
    renderStatus();
  }
  function sel(id, val, opts) {
    return '<select id="' + id + '" style="background:#140a28;color:#ccd6f6;border:1px solid rgba(0,240,255,.25);border-radius:6px;padding:4px 6px;font-size:.76rem">' +
      opts.map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === val ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select>';
  }
  function yes(b) { return b ? '<span style="color:#4ade80">yes</span>' : '<span style="color:#5a6a88">no</span>'; }
  function toggleSettings() {
    var p = document.getElementById('o2v-panel'); if (!p) return;
    if (p.style.display === 'block') { p.style.display = 'none'; return; }
    var inputCss = 'background:#140a28;color:#ccd6f6;border:1px solid rgba(0,240,255,.25);border-radius:6px;padding:4px 8px;font-size:.76rem';
    var engines = [['auto', 'Automatic'], ['gemini', 'Gemini'], ['native', 'Android speech'], ['browser', 'Browser speech']];
    p.innerHTML =
      '<div style="display:grid;grid-template-columns:auto 1fr;gap:6px 10px;align-items:center">' +
      '<span>Speech input</span>' + sel('o2v-stt', cfg.stt, engines) +
      '<span>Spoken replies</span>' + sel('o2v-tts', cfg.tts, engines) +
      '<span>Speak typed replies</span><label><input type="checkbox" id="o2v-auto"' + (cfg.speakReplies ? ' checked' : '') + '> read every Lumenis reply aloud</label>' +
      '<span>Gemini voice</span><input id="o2v-voice" value="' + String(cfg.voice || 'Kore').replace(/"/g, '') + '" style="' + inputCss + ';width:120px">' +
      '<span>Language</span><input id="o2v-lang" value="' + String(cfg.lang || '').replace(/"/g, '') + '" style="' + inputCss + ';width:120px">' +
      '<span>Gemini key</span><span style="display:flex;gap:6px;flex-wrap:wrap"><input id="o2v-key" type="password" autocomplete="off" placeholder="' + (deviceKey() ? 'saved on this device' : 'paste key (kept on this device only)') + '" style="' + inputCss + ';flex:1;min-width:160px">' +
      '<button id="o2v-keysave" style="' + B + ';height:28px">Save</button><button id="o2v-keyclr" style="' + B + ';height:28px">Clear</button></span>' +
      '</div>' +
      '<div style="margin-top:8px;color:#8fa3c7;line-height:1.6">Models: ' + cfg.sttModel + ' (speech to text), ' + cfg.ttsModel + ' (voice).<br>' +
      'Detected here: reactor Gemini proxy ' + (caps.proxyChecked ? yes(caps.proxy) : '…') + ' · device Gemini key ' + yes(!!deviceKey()) +
      ' · microphone ' + yes(caps.mic && caps.recorder) + ' · Android speech in ' + yes(caps.nativeStt) + ' / out ' + yes(caps.nativeTts) +
      ' · browser recognition ' + yes(caps.browserStt) + ' · browser voices ' + (caps.browserVoices || 0) + '<br>' +
      'Now using: input ' + (ENGINE_NAMES[sttEngine()] || 'none') + ', output ' + (ENGINE_NAMES[ttsOrder()[0]] || 'none') + '.</div>';
    p.style.display = 'block';
    function upd() {
      cfg.stt = document.getElementById('o2v-stt').value; cfg.tts = document.getElementById('o2v-tts').value;
      cfg.speakReplies = document.getElementById('o2v-auto').checked;
      cfg.voice = (document.getElementById('o2v-voice').value || 'Kore').replace(/[^A-Za-z]/g, '') || 'Kore';
      cfg.lang = (document.getElementById('o2v-lang').value || '').trim();
      saveCfg(); renderStatus();
    }
    ['o2v-stt', 'o2v-tts', 'o2v-auto', 'o2v-voice', 'o2v-lang'].forEach(function (id) { document.getElementById(id).onchange = upd; });
    document.getElementById('o2v-keysave').onclick = function () {
      var v = document.getElementById('o2v-key').value.trim();
      if (!/^[A-Za-z0-9_\-]{20,}$/.test(v)) { sys('Voice: that does not look like a Gemini API key.'); return; }
      try { localStorage.setItem(GKEY, v); } catch (_) {}
      document.getElementById('o2v-key').value = '';
      sys('Voice: Gemini key saved on this device.'); p.style.display = 'none'; toggleSettings(); renderStatus();
    };
    document.getElementById('o2v-keyclr').onclick = function () {
      try { localStorage.removeItem(GKEY); } catch (_) {}
      sys('Voice: Gemini key removed from this device.'); p.style.display = 'none'; toggleSettings(); renderStatus();
    };
  }
  var PH = { idle: '', listening: 'Listening…', transcribing: 'Transcribing…', thinking: 'Lumenis is thinking…', speaking: 'Speaking…' };
  function renderLevel() { var l = document.getElementById('o2v-lvl'); if (l) l.style.width = Math.round(st.level * 100) + '%'; }
  function renderStatus() {
    var bar = document.getElementById('o2v-bar'); if (!bar) return;
    var active = st.phase !== 'idle' || st.live;
    bar.style.display = active || st.note ? 'flex' : 'none';
    document.getElementById('o2v-phase').textContent = st.live ? 'LIVE · ' + (PH[st.phase] || 'Ready') : (PH[st.phase] || '');
    document.getElementById('o2v-note').textContent = st.note || '';
    var se = sttEngine(), te = ttsOrder()[0];
    document.getElementById('o2v-eng').textContent = (se ? ENGINE_NAMES[se] : 'no input') + ' → ' + (cfg.muted ? 'muted' : (te ? ENGINE_NAMES[te] : 'no voice'));
    document.getElementById('o2v-stop').style.display = active ? 'inline-flex' : 'none';
    var mic = document.getElementById('o2v-mic'), live = document.getElementById('o2v-live'), spk = document.getElementById('o2v-spk');
    if (mic) {
      var rec = st.phase === 'listening' && !st.live;
      mic.style.background = rec ? 'rgba(255,0,212,.25)' : 'rgba(0,0,0,.35)';
      mic.innerHTML = rec ? '<i class="fas fa-paper-plane"></i>' : '<i class="fas fa-microphone"></i>';
      mic.title = rec ? 'Send what you said' : 'Speak to Lumenis (tap again to send)';
      mic.disabled = st.live; mic.style.opacity = st.live ? '.4' : '1';
      if (!se) mic.title = noSttReason();
    }
    if (live) {
      live.style.background = st.live ? 'linear-gradient(135deg,#ff00d4,#7a00ff)' : 'rgba(0,0,0,.35)';
      live.querySelector('span').textContent = st.live ? 'End live' : 'Live';
    }
    if (spk) {
      spk.innerHTML = cfg.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
      spk.title = cfg.muted ? 'Voice muted (tap to unmute)' : 'Mute Lumenis\'s voice';
      spk.style.color = cfg.muted ? '#ff7a9a' : '#ccd6f6';
    }
  }
  new MutationObserver(function () { inject(); }).observe(document.documentElement, { childList: true, subtree: true });
  inject();

  window.O2Voice = {
    version: '1.0',
    caps: function () { return JSON.parse(JSON.stringify(caps)); },
    engines: function () { return { stt: sttEngine(), tts: ttsOrder() }; },
    state: function () { return { phase: st.phase, live: st.live, muted: cfg.muted, error: st.error }; },
    startLive: startLive, stopLive: stopLive, stopAll: stopAll, pushToTalk: pushToTalk,
    speak: speak, stopSpeaking: stopSpeaking, ready: function () { return proxyReady; },
    lastSpoken: function () { return st.lastSpoken; },
    _isEcho: isEcho
  };
})();
