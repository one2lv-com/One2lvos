"""Test package.

Every test (and every subprocess a test starts) uses a throwaway data
folder, so running the suite never touches the lab's real data/ stores.
"""

import os
import tempfile

if not os.environ.get("NIMLAB_TEST_KEEP_DATA_DIR"):
    os.environ["NIMLAB_DATA_DIR"] = os.path.join(tempfile.mkdtemp(prefix="nimlab_test_"), "data")
if not os.environ.get("NIMLAB_TEST_KEEP_OUTPUT_DIR"):
    os.environ["NIMLAB_OUTPUT_DIR"] = os.path.join(tempfile.mkdtemp(prefix="nimlab_out_"), "output")
# the v3.2 role migration rewrites config_cluster.json once; tests read the
# real config but must never write it
os.environ["NIMLAB_CONFIG_READONLY"] = "1"
# the saved MCP key lives outside the project; tests use a throwaway file
os.environ["NIMLAB_SECRETS"] = os.path.join(tempfile.mkdtemp(prefix="nimlab_secrets_"), "secrets.json")
# output is compared as plain text; the colour tests turn colour on themselves
os.environ["NIMLAB_COLOR"] = "0"
