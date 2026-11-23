"""Testbed menu for NVCF gRPC models (v3.5): list them, set / refresh /
clear function IDs, set an ASR language, check an ID, try ASR or TTS."""

from . import colors as C, nvcf_grpc, store


def _pick(rows, ask, label="Model number or id"):
    s = ask(f"{label}: ").strip()
    if not s:
        return None
    if s.isdigit() and 1 <= int(s) <= len(rows):
        return rows[int(s) - 1]["model"]
    hits = [r["model"] for r in rows if s.lower() in r["model"].lower()]
    return hits[0] if len(hits) == 1 else (s if "/" in s else None)


MENU = (("Function IDs", (("1", "Paste an ID", "from the Try API sample"),
                          ("2", "Refresh IDs", "from build.nvidia.com"),
                          ("3", "Clear an ID", ""),
                          ("4", "Check an ID works", "needs the NVIDIA key"))),
        ("Per model", (("5", "Language", "language_code, e.g. es-US"),
                       ("6", "ASR mode", "offline / streaming"))),
        ("Try it", (("7", "Try ASR", "on an audio file"), ("8", "Try TTS", ""))))


def run_menu(ask=input, out=print, orch=None):
    from .cli import grpc_lines
    nvcf_grpc.seed_from_spec_cache()
    while True:
        rows = nvcf_grpc.rows()
        ok, detail = nvcf_grpc.available()
        out("\n" + C.header("NVCF gRPC models"))
        out(C.dim(f"endpoint {nvcf_grpc.URI}; client: ") + (C.ok(detail) if ok else C.err("not installed: " + detail)))
        for line in grpc_lines(rows) or ["  none yet: run the 200 sweep first (launcher: Discover & Sweep)"]:
            out(line)
        out(C.rule(50))
        for title, entries in MENU:
            out(C.section(title))
            for k, t, extra in entries:
                out(C.entry(k, t, extra))
        out(C.entry(0, "Back"))
        c = ask("Choice: ").strip()
        if c in ("0", "", "q"):
            return
        if c == "2":
            m = _pick(rows, ask, "Model number/id (Enter = all)") if rows else None
            for mid in ([m] if m else [r["model"] for r in rows]):
                if not m and nvcf_grpc.record(mid).get("source") in store.GRPC_USER_SOURCES:
                    out(C.dim(f"  {mid}: kept your pasted ID"))
                    continue
                good, msg = nvcf_grpc.refresh(mid)
                out((C.ok("  [ok] ") if good else C.err("  [x] ")) + msg)
            continue
        if c not in "1345678" or len(c) != 1:
            continue
        m = _pick(rows, ask)
        if not m:
            out(C.warn("No such model."))
            continue
        if c == "1":
            fid = ask(f"Function ID for {m} (from its \"Try API\" sample: --metadata function-id \"...\"): ").strip()
            try:
                store.set_grpc_function(m, fid.strip('"\''), source="user", kind=nvcf_grpc.kind_of(m))
                out(C.ok(f"[ok] saved for {m}"))
            except ValueError as e:
                out(C.err(str(e)))
        elif c == "3":
            out(C.ok("[ok] cleared") if store.clear_grpc_function(m) else "nothing stored")
        elif c == "5":
            v = ask("language_code (e.g. en-US, es-US, de-DE, multi; '-' = model default): ").strip()
            store.update_grpc_settings(m, language_code=None if v in ("", "-") else v)
            out(C.ok("[ok]"))
        elif c == "6":
            v = ask("offline / streaming / - : ").strip().lower()
            if v in ("offline", "streaming", "-"):
                store.update_grpc_settings(m, mode=None if v == "-" else v)
                out(C.ok("[ok]"))
        elif c == "4":
            if not ok:
                out(C.err(detail))
                continue
            fid = nvcf_grpc.function_id(m)
            if not fid:
                out(C.warn("No function ID yet (option 1 or 2)."))
                continue
            try:
                good, lat, det = nvcf_grpc.client().check(fid, nvcf_grpc.kind_of(m, nvcf_grpc.record(m)))
            except nvcf_grpc.Unavailable as e:
                out(C.err(str(e)))
                continue
            store.note_grpc_check(m, good, det, latency=lat)
            out((C.ok("[ok] ") if good else C.err("[x] ")) + f"{det} ({lat}s)")
            if not good:
                h = nvcf_grpc.stale_hint(m, det.split(":")[0], det)
                if h:
                    out(C.warn(h))
        elif c == "7":
            path = ask("Audio file: ").strip().strip("'\"")
            lang = ask(f"language_code [{nvcf_grpc.asr_language({}, nvcf_grpc.record(m))}]: ").strip()
            sp = {"model": m}
            if lang:
                sp["language_code"] = lang
            r = nvcf_grpc.run_asr(sp, path=path)
            out((C.ok(f"[ok] {r.latency}s: ") + (r.text or "(empty)")) if r.ok else C.err(r.error))
        elif c == "8":
            from .api import play_audio, save_wav
            text = ask("Text: ").strip() or "Hello from the NIM lab over NVCF gRPC."
            r = nvcf_grpc.run_tts({"model": m}, text)
            if r.ok:
                p = save_wav(r.data, "grpc_tts")
                out(C.ok(f"[ok] {p} ({r.latency}s)"))
                play_audio(p)
            else:
                out(C.err(r.error))
