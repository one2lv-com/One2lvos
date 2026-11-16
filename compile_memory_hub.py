#!/usr/bin/env python3
"""compile_memory_hub.py — run Lumenis's memory compile loop / upkeep from the command line.

  python3 compile_memory_hub.py                 # compile now (expire due rows, write canonical memory)
  python3 compile_memory_hub.py --dry-run       # report only, change nothing
  python3 compile_memory_hub.py --upkeep daily|weekly|monthly
  python3 compile_memory_hub.py --import memory_layers/MEMORY.md
  python3 compile_memory_hub.py --restore data/memory_hub/runs/<file>.json   # undo an expiry/archive run
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lumenis_reactor_core.compass import FluxCompass  # noqa: E402
from lumenis_reactor_core import memory_hub as hub  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--upkeep", choices=["daily", "weekly", "monthly"])
ap.add_argument("--import", dest="import_path")
ap.add_argument("--restore")
a = ap.parse_args()
c = FluxCompass()
if a.import_path:
    out = hub.import_memory_md(c, a.import_path)
elif a.restore:
    out = hub.restore(c, a.restore)
elif a.upkeep:
    out = hub.upkeep(c, force=a.upkeep)
else:
    out = hub.compile(c, dry_run=a.dry_run)
print(json.dumps(out, indent=1, default=str))
