# Lumenis live vision

Lumenis can look at a screen or stream the owner chooses to share. Frames are sampled every few seconds, sent one
at a time to an NVIDIA-hosted vision model, and each reading goes into his context as a labelled observation.

## How to use it

1. Open `/vision` on the reactor (owner side, e.g. `https://lumenis.one2lv.com/vision`, behind Cloudflare Access).
2. **Share a screen:** press Start sharing and pick the Brawlhalla window. The browser shows its own sharing
   indicator; the browser's Stop sharing button or the page's Stop ends the session.
   **Or pull a stream:** paste an RTSP / RTMP / SRT / HLS / HTTP URL that ffmpeg can read (for example an OBS
   stream served by MediaMTX). Local/private addresses are blocked unless `LUMENIS_VISION_ALLOW_LOCAL=1`.
3. Readings appear on the page and in Lumenis' chat context while they are under 30 seconds old.

## Pipeline

`lumenis_reactor_core/vision.py`

- Intake: browser JPEG uploads (`POST /api/vision/frame`) or an ffmpeg puller for stream URLs.
- Validation: JPEG/PNG/WebP only, 4 MB cap, 32 px to 8192 px, decoded and re-encoded (drops metadata and
  trailing data), downscaled to 1280 px. Stream URLs: scheme allowlist, DNS check, link-local/metadata always
  blocked, ffmpeg protocol whitelist.
- Backpressure: one model call in flight; a newer frame replaces an unanalysed one (counted as dropped).
- Limits: interval 1.5 to 60 s (default 3), 20 model calls per minute, sessions end after 120 minutes, or after
  90 seconds without browser frames.
- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` (thinking off), fallback
  `nvidia/nemotron-3.5-super-vl-120b-a12b`, on `integrate.api.nvidia.com`. Override with
  `LUMENIS_VISION_MODEL` / `LUMENIS_VISION_FALLBACK_MODEL`.
- Output: JSON per frame (scene, game, summary, players, HUD text, events, callout, confidence, cannot_tell) plus
  captured/received/analysed timestamps, inference time, end-to-end time and age. Stored in memory (last 100)
  and as text in `data/vision/observations.jsonl` (git-ignored). Frames are never written to disk.
- Council: owner turns get a "Live vision" line in the status block (OFF, or the last three fresh readings
  marked as observations, not verified facts). Guests get nothing. Nothing goes to facts or memory.

## For other parts of the reactor (Discord voice)

- `GET /api/vision/status` - session, counters, limits, latest reading
- `GET /api/vision/latest?since=<id>` - readings newer than `id`
- `GET /api/vision/events` - Server-Sent Events, one JSON reading per event
- In process: `vision.latest()`, `vision.subscribe()`, `vision.prompt_block()`

Each reading has `callout` (at most 8 words, or null) and `fresh_s`. Speak only callouts a few seconds old.
Vision never speaks or posts by itself.

## What it cannot do

- It sees pixels from single frames. Hitboxes, hurtboxes, cooldowns, frame data, inputs and off-screen state are
  not visible, and the model is told to say so.
- About 2 to 4 seconds from capture to reading on the hosted model: fine for "what's going on", too slow for
  frame-perfect reactions.
- Discord bots cannot receive Go Live / screen-share video through Discord's bot API, and Steam exposes no bot
  video feed, so Steam/Discord video has to come in through the `/vision` screen share or an OBS stream.

## NVIDIA VSS blueprint (not used)

VSS is a self-hosted Docker/Helm deployment that needs NVIDIA data-centre GPUs and an NGC key; it does not run on
the reactor host (no GPU). The hosted API catalog used here is free for Developer Program members for
prototyping, development and testing, with a requests-per-minute limit (about 40 RPM on most models per NVIDIA's
FAQ); production use needs NVIDIA AI Enterprise. The same key also serves Lumenis' chat, so vision calls share
that limit.

## Tests

- `tests/test_vision.py` - unit tests, stubbed model, no network
- `tests/vision_live_test.py browser|stream <video> [seconds]` - real NVIDIA inference through both intake paths
- `tests/vision_council_test.py <video>` - what Lumenis says with vision off/on, hidden info, guest
- Results: `tests/vision_results.json`
