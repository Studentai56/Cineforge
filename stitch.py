"""Encode per-scene frames into clips and stitch them into the final video with ffmpeg."""
import shutil
import subprocess
from pathlib import Path


def _ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _probe_duration(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        return float(out)
    except Exception:
        return None


def _has_audio(path: Path) -> bool:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=index", "-of", "csv=p=0", str(path)],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        return bool(out)
    except Exception:
        return False


def encode_scene(frames_dir: Path, out_mp4: Path, W: int, H: int, fps: int, pixel: bool) -> None:
    scale = f"scale={W}:{H}:flags=neighbor" if pixel else f"scale={W}:{H}"
    _ffmpeg(
        [
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-vf", scale,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "20",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
    )


def _mux_audio(video: Path, audio: Path, out: Path) -> Path:
    vd = _probe_duration(video) or 0.0
    ad = _probe_duration(audio) or 0.0
    rate = 1.0
    if vd > 0 and ad > 0:
        rate = max(0.5, min(2.0, ad / vd))  # fit narration to the clip
    _ffmpeg(
        [
            "-i", str(video), "-i", str(audio),
            "-filter_complex", f"[1:a]atempo={rate:.3f}[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
        ]
    )
    return out


def stitch(
    jobdir: Path,
    total: int,
    W: int,
    H: int,
    secs: float,
    music: bool,
    stub: bool = False,
    pixel: bool = False,
    audio_dir: Path | None = None,
) -> None:
    jobdir = Path(jobdir)
    fps = max(6, round(25 / max(1, secs)))
    scene_mp4s = []

    for i in range(total):
        if stub:
            video = jobdir / f"scene_{i}.mp4"
        else:
            frames_dir = jobdir / "scenes" / str(i)
            video = jobdir / f"scene_{i}.mp4"
            encode_scene(frames_dir, video, W, H, fps, pixel)

        audio = Path(audio_dir) / f"scene_{i}.mp3" if audio_dir else None
        if audio is not None and audio.exists():
            video = _mux_audio(video, audio, jobdir / f"scene_{i}_v.mp4")
        scene_mp4s.append(video)

    concat_list = jobdir / "concat.txt"
    with open(concat_list, "w") as f:
        for m in scene_mp4s:
            f.write(f"file '{m.as_posix()}'\n")

    pre = jobdir / "pre.mp4"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(pre)])

    final = jobdir / "final.mp4"
    bg = Path(__file__).resolve().parent / "assets" / "bg.mp3"
    if music and bg.exists():
        if _has_audio(pre):
            _ffmpeg(
                ["-i", str(pre), "-i", str(bg),
                 "-filter_complex", "[1:a]volume=0.25[bg];[0:a][bg]amix=inputs=2:duration=shortest[a]",
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", str(final)]
            )
        else:
            _ffmpeg(["-i", str(pre), "-i", str(bg), "-map", "0:v", "-map", "1:a",
                     "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)])
    else:
        pre.replace(final)

    # Poster: first generated frame (real) or a ffmpeg-generated placeholder (stub).
    if stub:
        _ffmpeg(["-f", "lavfi", "-i", f"testsrc=size={W}x{H}:rate=1:duration=1",
                 "-frames:v", "1", str(jobdir / "poster.png")])
    else:
        first = jobdir / "scenes" / "0" / "frame_0000.png"
        if first.exists():
            shutil.copy(first, jobdir / "poster.png")
