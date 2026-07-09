"""Animate a still image into a short clip using Stable Video Diffusion (SVD).

LTX-Video-2B is offered as a higher-quality alternative and falls back to SVD
automatically if it fails to load on your setup.
"""
from pathlib import Path

import torch

_SVD = None
_LTX = None


def get_svd():
    global _SVD
    if _SVD is None:
        from diffusers import StableVideoDiffusionPipeline

        print("[anim] loading SVD:", "stabilityai/stable-video-diffusion-img2vid-xt", flush=True)
        _SVD = StableVideoDiffusionPipeline.from_pretrained(
            "stabilityai/stable-video-diffusion-img2vid-xt",
            torch_dtype=torch.float16,
            variant="fp16",
        )
        _SVD.enable_attention_slicing()
        _SVD.enable_model_cpu_offload()
        print("[anim] SVD ready", flush=True)
    return _SVD


def _save_frames(frames, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, fr in enumerate(frames):
        fr.save(out_dir / f"frame_{i:04d}.png")
    return len(frames)


def animate(image: Image.Image, out_dir: Path, model: str = "svd", height: int = 576, width: int = 1024) -> int:
    out_dir = Path(out_dir)
    img = image.resize((width, height))

    if model == "ltx":
        try:
            return _animate_ltx(img, out_dir)
        except Exception as e:  # noqa: BLE001
            print("[anim] LTX failed, falling back to SVD:", e, flush=True)

    svd = get_svd()
    num_frames = 25
    out = svd(
        img,
        num_frames=num_frames,
        decode_chunk_size=4,
        motion_bucket_id=127,
        noise_aug_strength=0.02,
    )
    frames = out.frames[0]
    return _save_frames(frames, out_dir)


def _animate_ltx(img: Image.Image, out_dir: Path) -> int:
    global _LTX
    if _LTX is None:
        from diffusers import LTXImageToVideoPipeline

        print("[anim] loading LTX:", "Lightricks/LTX-Video", flush=True)
        _LTX = LTXImageToVideoPipeline.from_pretrained(
            "Lightricks/LTX-Video", torch_dtype=torch.float16
        ).to("cuda")
        print("[anim] LTX ready", flush=True)

    out = _LTX(
        image=img,
        prompt="smooth camera motion, high quality, cinematic",
        num_frames=25,
        num_inference_steps=25,
    )
    frames = out.frames[0]
    return _save_frames(frames, out_dir)
