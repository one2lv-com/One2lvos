"""3.7.2: settings that look set but cannot work.

Setup and `nimlab doctor` flag them:
- voice_settings.tts_url (or asr_url) that points at a website homepage
  (https://nvidia.com) instead of a speech endpoint;
- a role whose model is a bare URL instead of a model id;
- role fallbacks ("fallback" / "fallbacks" on a role) that are bare URLs;
- a role endpoint that is a homepage.

Each finding is (where, problem, fix), in plain words.
"""

import urllib.parse

SPEECH_URL_KEYS = ("tts_url", "asr_url")


def is_url(text):
    return isinstance(text, str) and text.strip().lower().startswith(("http://", "https://"))


def is_homepage(url):
    """True for a URL with no path (or only '/'), e.g. https://nvidia.com:
    a website, not an API endpoint."""
    if not is_url(url):
        return False
    try:
        u = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return False
    return bool(u.netloc) and u.path in ("", "/") and not u.query


def _fallbacks(v):
    fb = v.get("fallbacks", v.get("fallback"))
    if fb is None:
        return []
    return fb if isinstance(fb, list) else [fb]


def find_problems(cluster):
    """-> [(where, problem, fix)] for config_cluster.json settings."""
    out = []
    cluster = cluster or {}
    vs = cluster.get("voice_settings") or {}
    for k in SPEECH_URL_KEYS:
        url = vs.get(k)
        if url and is_homepage(url):
            what = "speech (TTS)" if k == "tts_url" else "speech recognition (ASR)"
            out.append((f"voice_settings.{k}",
                        f"{url} is a website homepage, not a {what} endpoint",
                        f"set voice_settings.{k} in config_cluster.json to the endpoint that ends in "
                        f"/v1/audio/{'synthesize' if k == 'tts_url' else 'transcriptions'}, or remove it to use "
                        "the default"))
        elif url and not is_url(url):
            out.append((f"voice_settings.{k}", f"{url!r} is not a URL", f"remove {k} or give a full https:// URL"))
    for key, v in (cluster.get("roles") or {}).items():
        if isinstance(v, str):
            v = {"model": v}
        if not isinstance(v, dict):
            continue
        m = v.get("model")
        if is_url(m):
            out.append((f"roles.{key}", f"the model is a bare URL ({m}), not a model id",
                        "pick a model id with `nimlab setup roles` (a custom URL goes in the role's endpoint)"))
        ep = v.get("endpoint")
        if ep and is_homepage(ep):
            out.append((f"roles.{key}.endpoint", f"{ep} is a website homepage, not an API endpoint",
                        "give the full API URL (for example .../v1/chat/completions) or clear the endpoint"))
        for fb in _fallbacks(v):
            fm = fb.get("model") if isinstance(fb, dict) else fb
            if is_url(fm):
                out.append((f"roles.{key}.fallback", f"the fallback is a bare URL ({fm}), not a model id",
                            "list fallback models by id (for example nvidia/...), not web addresses"))
    return out


def lines(cluster):
    return [f"{where}: {problem}. Fix: {fix}" for where, problem, fix in find_problems(cluster)]
