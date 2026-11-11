import re, hashlib
import riva.client

SERVER = "grpc.nvcf.nvidia.com:443"
TTS_FID = "877104f7-e885-42b9-8de8-f6e4c6303969"  # magpie-tts-multilingual


def load_keys():
    """Return list of (hash, [var names], value), deduped by value. Never print value."""
    seen = {}
    order = []
    for f, tag in [("/home/sprite/One2lvos/.env", ""), ("/home/sprite/env_merge/other_agent_input.env", "other_agent_input.env:")]:
        for line in open(f):
            m = re.match(r'^([A-Z0-9_]*NVIDIA[A-Z0-9_]*)=(.*)$', line.strip())
            if not m:
                continue
            k, v = m.groups()
            v = v.strip().strip('"').strip("'")
            if not v.startswith("nvapi-"):
                continue
            h = hashlib.sha256(v.encode()).hexdigest()[:8]
            if h not in seen:
                seen[h] = ([], v)
                order.append(h)
            seen[h][0].append(tag + k)
    return [(h, seen[h][0], seen[h][1]) for h in order]


def auth(key, fid):
    return riva.client.Auth(None, True, SERVER, [["function-id", fid], ["authorization", "Bearer " + key]])


def short_err(e):
    s = str(e)
    code = getattr(e, "code", None)
    c = code().name if callable(code) else ""
    det = getattr(e, "details", None)
    d = det() if callable(det) else s
    d = re.sub(r'nvapi-[A-Za-z0-9_-]+', 'nvapi-***', d or "")
    return f"{c}: {d[:200]}"
