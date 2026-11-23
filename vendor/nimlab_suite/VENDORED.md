# NVIDIA lab suite (nimlab) inside the reactor

One2lv's NVIDIA NIM test lab, v3.8.6, from github.com/xcrystalxmariex-svn/nimlab at commit 16752dd
(2026-11-14), wired into Lumenis' tool engine as the `nimlab.*` namespace by
`lumenis_reactor_core/nimlab_tools.py`. Updated from v3.2.0 (ae5248a) on 2026-11-23; the old copy is
kept outside git in `backups/nimlab/`.

- The suite code here is unchanged from upstream. Kept One2lvOS-specific: this file, `seed/` and
  `.gitignore` (upstream's secret and wallet patterns added). Upstream's `data/` and shipped
  `config_*.json` are left out: the reactor's state and config live in `data/nimlab/`.
- The reactor imports it; it does not run `start.sh`.
- Every request the suite makes passes `nimlab_tools`' gate: NVIDIA hosts only, call budget, rate limit,
  and no safety/guard/classifier model (`model_guard.is_safety_model`), whoever picked the model.
- Autonomis reaches it with `autonomis-agent.py --nimlab TOOL --nimlab-args JSON`, through the
  reactor's L0-L3 tiers, and runs `nimlab.status` each cycle when `nimlab.monitor` is on in
  `autonomis-config.json`.
- `seed/` holds the suite's pre-3.1 registry files. On first use the reactor copies them to
  `data/nimlab/` (gitignored), where the suite's own migration turns them into its data stores.
- Runtime state (stores, config, WAVs, caches) lives in `data/nimlab/`, never in this folder.
- The suite's MCP bridge, sweeps, discovery, voice cloning, role changes and image generation are not
  exposed to Lumenis. Image generation goes through the Image app only.
- Tests: `python3 -m unittest discover -s tests -t .` from this folder (offline, HTTP mocked).
  Known on this host (2026-11-23, 1321 tests): `test_v386_audio_setup` only imports with
  `PYTHONPATH=tests:.` (then OK); `test_ubuntu_pep668_micro_vps` fails upstream too (the host's
  cloudflared is found, so the expected install hint is not printed); `test_shipped_config_has_every_cluster_section`
  fails because the shipped config is deliberately left out here (see above).
  The `nvapi-...` strings in tests/ are fake fixtures, not keys.
