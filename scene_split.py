"""Turn a free-form script into a list of scene prompts."""
import re


def split_scenes(script: str) -> list[str]:
    text = (script or "").strip()
    if not text:
        return []

    # 1) Explicit "SCENE:" markers take priority.
    if re.search(r"(?mi)^\s*SCENE\s*:", text):
        parts = re.split(r"(?mi)^\s*SCENE\s*:\s*", text)
        scenes = [p.strip() for p in parts[1:] if p.strip()]
        if scenes:
            return scenes

    # 2) Blank-line separated blocks.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        return blocks

    # 3) Single paragraph: group sentences (~2 per scene).
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= 1:
        return [text]

    scenes = []
    group = 2
    for i in range(0, len(sentences), group):
        scenes.append(" ".join(sentences[i : i + group]))
    return scenes
