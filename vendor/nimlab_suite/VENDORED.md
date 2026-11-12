# NVIDIA lab suite (nimlab) inside the reactor

One2lv's NVIDIA NIM test lab, v3.2, copied from `nvidia_laboratory_suite.zip` (2026-11-11) and wired into
Lumenis' tool engine as the `nimlab.*` namespace by `lumenis_reactor_core/nimlab_tools.py`.

- The suite code here is unchanged from the zip. The reactor imports it; it does not run `start.sh`.
- `seed/` holds the suite's pre-3.1 registry files. On first use the reactor copies them to
  `data/nimlab/` (gitignored), where the suite's own migration turns them into its data stores.
- Runtime state (stores, config, WAVs, caches) lives in `data/nimlab/`, never in this folder.
- The suite's MCP bridge, sweeps, discovery, voice cloning, role changes and image generation are not
  exposed to Lumenis. Image generation goes through the Image app only.
- Tests: `python3 -m unittest discover -s tests -t .` from this folder (offline, HTTP mocked).
  The `nvapi-...` strings in tests/ are fake fixtures, not keys.
