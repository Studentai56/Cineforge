"""Orchestrate one generation job: script -> scenes -> images -> animation -> stitch."""
import subprocess
import time
from pathlib import Path

from models_config import style_cfg
from scene_split import split_scenes

# Rotated through when "different voices per scene" is enabled.
MULTI_VOICE_IDS = [
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
]


def _resolution_wh(res: str, ratio: str) -> tuple[int, int]:
    if ratio == "9:16":
        return (480, 854) if res == "480p" else (720, 1280)
    return (854, 480) if res == "480p" else (1280, 720)


def _gen_dims(ratio: str) -> tuple[int, int]:
    # SDXL / SVD native orientation.
    return (1024, 576) if ratio == "16:9" else (576, 1024)


def run_pipeline(job_id, request: dict, jobdir: Path, stub: bool, update) -> None:
    jobdir = Path(jobdir)
    style = request.get("style", "cinematic")
    script = request.get("script", "")
    opts = request.get("options", {}) or {}
    res = opts.get("resolution", "480p")
    ratio = opts.get("ratio", "16:9")
    secs = float(opts.get("secondsPerScene", 4))
    model = opts.get("model", "svd")
    music = bool(opts.get("music", False))
    voiceover = bool(opts.get("voiceover", False))
    voice = opts.get("voice", "en-US-GuyNeural")
    multi_voice = bool(opts.get("multiVoice", False))
    cfg = style_cfg(style)
    pixel = bool(cfg.get("pixel"))

    W, H = _resolution_wh(res, ratio)
    gen_h, gen_w = _gen_dims(ratio)
    voice_ids = MULTI_VOICE_IDS if multi_voice else [voice]

    update(stage="script", progress=3)
    scenes = split_scenes(script)
    total = max(1, len(scenes))
    update(sceneTotal=total, sceneDone=0, progress=5)
    print(f"[pipeline] {total} scene(s), style={style}, model={model}, res={res}, ratio={ratio}", flush=True)

    if stub:
        for i in range(total):
            update(stage="images", sceneDone=i, progress=5 + int(35 * (i + 0.5) / total))
            time.sleep(0.4)
            update(stage="animating", sceneDone=i + 1, progress=5 + int(80 * (i + 1) / total))
            time.sleep(0.4)
        if voiceover:
            _stub_audio(jobdir, total, secs)
        update(stage="stitching", progress=92)
        time.sleep(0.2)
        from stitch import stitch

        stitch(jobdir, total, W, H, secs, music, stub=True, pixel=pixel, audio_dir=(jobdir / "audio") if voiceover else None)
        update(stage="done", status="done", progress=100, output="final.mp4")
        return

    from generate_images import generate
    from animate import animate
    from stitch import stitch
    from tts import generate_voiceover

    if voiceover:
        update(stage="script", progress=4)
        generate_voiceover(scenes, voice_ids, jobdir / "audio")
        update(progress=5)

    for i, scene in enumerate(scenes):
        update(stage="images", sceneDone=i, progress=5 + int(35 * (i + 0.5) / total))
        img = generate(scene, cfg, height=gen_h, width=gen_w)
        sdir = jobdir / "scenes" / str(i)
        sdir.mkdir(parents=True, exist_ok=True)
        img.save(sdir / "scene.png")

        update(stage="animating", sceneDone=i + 1, progress=5 + int(80 * (i + 1) / total))
        animate(img, sdir, model=model, height=gen_h, width=gen_w)

    update(stage="stitching", progress=92)
    stitch(
        jobdir,
        total,
        W,
        H,
        secs,
        music,
        stub=False,
        pixel=pixel,
        audio_dir=(jobdir / "audio") if voiceover else None,
    )
    update(stage="done", status="done", progress=100, output="final.mp4")


def _stub_audio(jobdir: Path, total: int, secs: float) -> None:
    adir = jobdir / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    for i in range(total):
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-t", str(secs), "-acodec", "libmp3lame", str(adir / f"scene_{i}.mp3")],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def prefetch() -> None:
    """Download model weights once (without loading them into RAM)."""
    from huggingface_hub import snapshot_download

    from models_config import BASE_MODEL, SVD_MODEL, LTX_MODEL

    for repo in (BASE_MODEL, SVD_MODEL, LTX_MODEL):
        print("[prefetch] downloading", repo, flush=True)
        try:
            snapshot_download(repo)
        except Exception as e:  # noqa: BLE001
            print("[prefetch] failed:", repo, e, flush=True)
    print("[prefetch] done", flush=True)
