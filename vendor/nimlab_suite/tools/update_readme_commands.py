"""Regenerate the README's Command reference from nimlab/commands.py.

Run after changing a command, a test or a symptom:
    python3 tools/update_readme_commands.py
tests/test_v374.py fails while the README section is stale.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nimlab import commands  # noqa: E402

if __name__ == "__main__":
    changed = commands.update_readme(os.path.join(ROOT, "README.md"))
    print("README.md updated" if changed else "README.md already up to date")
