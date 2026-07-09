"""SDXL image generation per scene, with optional style LoRA and pixel post-process."""
from PIL import Image

_PIPE = None


def get_pipe(style_cfg: dict):
    global _PIPE
    if _PIPE is not None:
        return _PIPE

    import torch
    from diffusers import StableDiffusionXLPipeline

    base = style_cfg.get("base_model") or "stabilityai/stable-diffusion-xl-base-1.0"
    print("[gen] loading SDXL base:", base, flush=True)
    _PIPE = StableDiffusionXLPipeline.from_pretrained(
        base,
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    )
    _PIPE.enable_attention_slicing()
    _PIPE.enable_model_cpu_offload()  # keep VRAM low for 8-16GB cards

    lora = style_cfg.get("lora_repo")
    if lora:
        print("[gen] loading LoRA:", lora, flush=True)
        _PIPE.load_lora_weights(lora, adapter_name="style")
        _PIPE.set_adapters(["style"], adapter_weights=[style_cfg.get("lora_weight", 0.8)])

    print("[gen] SDXL ready", flush=True)
    return _PIPE


def _pixelate(img: Image.Image, factor: int) -> Image.Image:
    small = img.resize((max(1, img.width // factor), max(1, img.height // factor)), Image.NEAREST)
    return small.resize((img.width, img.height), Image.NEAREST)


def generate(scene_text: str, style_cfg: dict, height: int = 576, width: int = 1024) -> Image.Image:
    pipe = get_pipe(style_cfg)
    prompt = scene_text.trim() + ", " + style_cfg.get("prompt_suffix", "")
    neg = style_cfg.get("negative_prompt", "")
    steps = int(style_cfg.get("steps", 25))

    img = pipe(
        prompt=prompt,
        negative_prompt=neg,
        num_inference_steps=steps,
        height=height,
        width=width,
    ).images[0]

    if style_cfg.get("pixel"):
        img = _pixelate(img, int(style_cfg.get("pixel_factor", 14)))

    return img
