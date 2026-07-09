"""Style + model registry shared by the pipeline.

The UI (lib/styles.ts) only needs presentation metadata; this file holds the
actual generation parameters. LoRAs are optional: styles work on prompt
engineering alone, and you can drop in a Hugging Face LoRA repo to push the
look further (see README).
"""

# SDXL base checkpoint. Swap for a style-specific base if you have one.
BASE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

# Animation models.
SVD_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"
LTX_MODEL = "Lightricks/LTX-Video"

# Per-style generation parameters.
STYLE_CONFIG = {
    "cinematic": {
        "prompt_suffix": (
            "cinematic film still, dramatic lighting, shallow depth of field, "
            "anamorphic lens flare, film grain, 35mm, highly detailed, moody color grade"
        ),
        "negative_prompt": "cartoon, anime, illustration, 3d render, low quality, blurry, deformed, watermark",
        "lora_repo": None,
        "lora_weight": 0.8,
        "steps": 25,
    },
    "anime": {
        "prompt_suffix": (
            "anime key visual, cel shading, vibrant colors, clean linework, "
            "studio anime style, masterpiece, detailed background"
        ),
        "negative_prompt": "realistic photo, 3d render, blurry, low quality, deformed hands, watermark",
        "lora_repo": None,
        "lora_weight": 0.85,
        "steps": 25,
    },
    "3d": {
        "prompt_suffix": (
            "3d render, CGI, pixar style, volumetric lighting, subsurface scattering, "
            "octane render, smooth shaded, dimensional, studio lighting"
        ),
        "negative_prompt": "2d, flat, sketch, anime, realistic photo, low quality, blurry",
        "lora_repo": None,
        "lora_weight": 0.8,
        "steps": 25,
    },
    "realistic": {
        "prompt_suffix": (
            "photorealistic photograph, natural lighting, sharp focus, "
            "highly detailed, 8k, real skin and materials, candid"
        ),
        "negative_prompt": "painting, illustration, anime, 3d render, cartoon, blurry, deformed, watermark",
        "lora_repo": None,
        "lora_weight": 0.8,
        "steps": 25,
    },
    "pixel": {
        "prompt_suffix": (
            "pixel art, retro game sprite, 16-bit, limited color palette, "
            "crisp pixels, isometric video game asset"
        ),
        "negative_prompt": "smooth, realistic, blurry, 3d, gradient, anti-aliased, photographic",
        "lora_repo": None,
        "lora_weight": 0.8,
        "steps": 20,
        "pixel": True,  # downscale + nearest-neighbor upscale for chunky pixels
        "pixel_factor": 14,
    },
}


def style_cfg(style: str) -> dict:
    return STYLE_CONFIG.get(style, STYLE_CONFIG["cinematic"])
