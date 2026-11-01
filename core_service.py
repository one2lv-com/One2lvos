#!/usr/bin/env python3
"""Persistent HTTP service for the One2lv Unified OS core."""
import os
import signal
import time
from flask import Flask, jsonify
from unified_os import One2lvUnifiedOS

app = Flask(__name__)
os_instance = One2lvUnifiedOS(base_dir=os.getenv("ONE2LV_DATA_DIR", "/var/lib/one2lv"))
boot_started = time.time()

try:
    os_instance.boot(verbose=False)
except Exception as exc:
    # Keep the HTTP service alive so /health can report the failure.
    os_instance.online = False
    boot_error = str(exc)
else:
    boot_error = None

@app.get("/health")
def health():
    return jsonify({
        "service": "one2lv-core",
        "status": "ok" if os_instance.online else "degraded",
        "online": os_instance.online,
        "boot_error": boot_error,
        "uptime_seconds": round(time.time() - boot_started, 1),
    }), (200 if os_instance.online else 503)

@app.get("/status")
def status():
    if not os_instance.online:
        return jsonify({"online": False, "error": boot_error}), 503
    stats = os_instance.core_os.get_stats()
    return jsonify({
        "service": "one2lv-core",
        "online": True,
        "boot_time_ms": round(os_instance.boot_time or 0),
        "core": stats,
        "council": os_instance.council.get_status(),
        "delta": os_instance.delta.get_status(),
    })

@app.get("/ready")
def ready():
    return jsonify({"ready": bool(os_instance.online)})

def shutdown(*_args):
    if os_instance.online:
        try:
            os_instance.shutdown()
        except Exception:
            pass

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3002")), threaded=True)
