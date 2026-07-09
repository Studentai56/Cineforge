# 🎬 CineForge — Free, Unlimited, No-Signup Script-to-Video Studio

Turn a written **script** into a **video** in five styles — **cinematic, anime, 3D,
realistic, pixel art** — entirely on your own machine. No account, no credits,
no API key, no subscription.

> **Why it's actually free & unlimited:** generation runs **open-source models
> locally on your GPU** (SDXL for images + Stable Video Diffusion / LTX for
> animation). There is no server billing you — the only limit is your own
> hardware time and VRAM. "Unlimited" means there is no counter or paywall in
> the code, not that it's instant.

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | ≥ 18 (tested 24) | Runs the web UI + API |
| Python | **3.11 or 3.12** | ⚠️ Not 3.13/3.14 — PyTorch/Diffusers don't ship wheels for them yet |
| ffmpeg | any recent | Used for stitching (already on most systems) |
| NVIDIA GPU | 8–16 GB VRAM | For real generation. (Demo mode needs no GPU.) |

---

## Quick start

### Option A — See the UI working now (no GPU needed)

```bash
npm install
npm run dev            # terminal 1 — web app at http://localhost:3000
npm run stub-worker    # terminal 2 — ffmpeg-based fake generator
```

Open http://localhost:3000, paste a script, pick a style, hit **Generate**. The
stub worker produces a real, playable MP4 (ffmpeg test pattern) so you can watch
the full queue → progress → gallery flow end to end.

### Option B — Real AI generation (your GPU)

```bash
npm install
npm run setup          # creates a Python venv, installs PyTorch(CUDA)+deps
npm run dev            # terminal 1
npm run worker         # terminal 2 — real SDXL + SVD/LTX pipeline
```

First generation downloads a few GB of model weights (one-time). After that it's
all local.

Optional: pre-download weights up front with `npm run setup --prefetch`.

---

## How it works

```
Browser ──POST /api/generate──▶ Next.js API  (writes .jobs/queue/<id>.json)
   ▲                                 │
   │  poll /api/jobs/[id]            ▼
   └─────────────  Python worker (python/main.py)  ─────────────┐
                    • split script → scenes                      │
                    • SDXL image per scene (style LoRA/prompt)   │
                    • animate image → clip (SVD / LTX)           │
                    • ffmpeg stitch → .jobs/active/<id>/final.mp4│
                                                              writes status.json
```

- **No database, no auth.** Job state is JSON files under `.jobs/`. History is
  just a directory listing — which is also what makes "no signup / unlimited"
  trivially true.
- **Async by design.** Generation takes minutes per scene, so it's a queue +
  polling model, not a blocking request.
- **One job at a time** by default (safest for limited VRAM).

---

## Styles

| Style | Look | Model notes |
|-------|------|-------------|
| `cinematic` | Film-grade, anamorphic, grainy | prompt-driven |
| `anime` | Cel-shaded, vibrant 2D | prompt-driven |
| `realistic` | Photoreal | prompt-driven |
| `3d` | CGI / Pixar-like render | prompt-driven |
| `pixel` | Retro 8/16-bit sprites | downscale + nearest-neighbor upscale |

All styles run on the same SDXL base. To push a look further, add a
Hugging Face LoRA in `python/models_config.py` (`lora_repo` per style) — e.g. an
anime or pixel-art SDXL LoRA.

## Render settings

- **Resolution:** 480p (854×480) or 720p (1280×720).
- **Seconds / scene:** target clip length per scene (2–12s).
- **Animation model:** `svd` (fast, ~8–10 GB) or `ltx` (LTX-2B, higher quality,
  ~12 GB; auto-falls back to SVD if it fails to load).
- **Music:** mixes in `python/assets/bg.mp3` if you drop one there.

---

## Project structure

```
app/                 Next.js UI + API routes
  api/generate       POST a job
  api/jobs           list / get status / stream video+poster
  api/styles         style metadata
components/          Studio, StylePicker, ScriptInput, SettingsPanel,
                     JobProgress, VideoCard, Gallery
lib/                 types.ts (job contract), styles.ts, jobs.ts (file store)
python/              generation backend (run by the worker)
  main.py            worker loop
  pipeline.py        orchestrator + model prefetch
  scene_split.py     script → scenes
  generate_images.py SDXL + optional LoRA + pixel post-process
  animate.py         SVD / LTX animation
  stitch.py          ffmpeg encode + concat
  models_config.py   style → model/prompt registry
scripts/             setup.mjs (venv+deps), run-worker.mjs, stub-worker.mjs
.jobs/               queue + active jobs (created at runtime)
```

---

## Tuning for your GPU

In `python/models_config.py` / `python/main.py`:

- **OOM at 8 GB:** keep **480p**, use **SVD**, lower `steps`, and rely on
  `enable_model_cpu_offload()` (already on). Avoid LTX.
- **16 GB+:** try **720p** and **LTX** for longer, higher-quality clips.
- Generation is sequential per job. For multiple GPUs you could run multiple
  workers, but that's out of scope for v1.

---

## Limitations (honest)

- "Free / unlimited" = **your** open-source models on **your** hardware. Bounded
  by your time and VRAM, not by a counter.
- First run downloads several GB of weights (one-time).
- 8–16 GB VRAM → short clips (a few seconds/scene) at 480–720p. Full-HD / long
  films need more VRAM.
- This is a **local app**. To share it remotely, put it behind a tunnel/VPN
  (and remember there's no auth — anyone who can reach it can generate).
```
