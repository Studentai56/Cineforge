"""CineForge generation worker.

Watches .jobs/queue, runs the pipeline for each job, and writes status under
.jobs/active/<id>/. Run with:  npm run worker   (after `npm run setup`)

Flags:
  --stub     simulate generation with ffmpeg (no GPU / torch needed)
  --once     process a single queued job then exit
  prefetch   download model weights once, then exit
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / ".jobs" / "queue"
ACTIVE = ROOT / ".jobs" / "active"
MODE_FILE = ROOT / ".jobs" / ".mode"

STUB = os.environ.get("CINEFORGE_STUB") == "1"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def claim_job():
    QUEUE.mkdir(parents=True, exist_ok=True)
    files = sorted(QUEUE.glob("*.json"))
    if not files:
        return None
    f = files[0]
    try:
        data = json.loads(f.read_text())
    except Exception:
        f.unlink(missing_ok=True)
        return None
    job_id = data.get("id")
    if not job_id:
        f.unlink(missing_ok=True)
        return None
    f.unlink(missing_ok=True)
    jobdir = ACTIVE / job_id
    jobdir.mkdir(parents=True, exist_ok=True)
    (jobdir / "request.json").write_text(json.dumps(data, indent=2))
    return job_id, data


def write_status(job_id: str, base: dict, **fields) -> None:
    base.update(fields)
    base["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (ACTIVE / job_id / "status.json").write_text(json.dumps(base, indent=2))


def run_one(stub: bool) -> bool:
    claimed = claim_job()
    if claimed is None:
        return False
    job_id, data = claimed
    request = data.get("request", {})
    base = {
        "id": job_id,
        "style": request.get("style", "cinematic"),
        "status": "processing",
        "stage": "queued",
        "progress": 0,
        "sceneTotal": 0,
        "sceneDone": 0,
        "createdAt": data.get("createdAt", time.strftime("%Y-%m-%dT%H:%M:%S")),
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "error": None,
        "output": None,
        "request": request,
    }
    write_status(job_id, base, status="processing", stage="script", progress=3)

    # Stub mode must pre-create scene clips (ffmpeg lavfi) before stitching.
    if stub:
        try:
            _prepare_stub_scenes(ACTIVE / job_id, job_id, request, base, write_status)
        except Exception as e:  # noqa: BLE001
            write_status(job_id, base, status="error", stage="done", error=str(e)[:500], progress=100)
            return True

    try:
        from pipeline import run_pipeline

        run_pipeline(job_id, request, ACTIVE / job_id, stub, lambda **kw: write_status(job_id, base, **kw))
    except Exception as e:  # noqa: BLE001
        log(f"ERROR in {job_id}: {e}")
        write_status(job_id, base, status="error", stage="done", error=str(e)[:500], progress=100)
    return True


def _prepare_stub_scenes(jobdir: Path, job_id: str, request: dict, base: dict, write_status) -> None:
    opts = request.get("options", {}) or {}
    res = opts.get("resolution", "480p")
    secs = float(opts.get("secondsPerScene", 4))
    from scene_split import split_scenes

    total = max(1, len(split_scenes(request.get("script", ""))))
    W, H = (854, 480) if res == "720p" else (1280, 720)
    import subprocess

    for i in range(total):
        write_status(job_id, base, stage="images", sceneDone=i, progress=5 + int(35 * (i + 0.5) / total))
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi",
             "-i", f"testsrc=size={W}x{H}:rate={max(6, round(25 / secs))}:duration={secs}",
             "-pix_fmt", "yuv420p", str(jobdir / f"scene_{i}.mp4")],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "prefetch":
        from pipeline import prefetch

        prefetch()
        return

    stub = STUB or ("--stub" in args)
    once = "--once" in args
    MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text("stub" if stub else "real")
    log(f"worker started (stub={'yes' if stub else 'no'})")
    while True:
        if run_one(stub):
            if once:
                break
        else:
            time.sleep(2)


if __name__ == "__main__":
    main()
