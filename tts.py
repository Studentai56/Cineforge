"""Free, key-less text-to-speech voice-over via edge-tts (Microsoft's public
endpoint). One mp3 per scene, so the worker can align narration to each clip.

Requires: pip install edge-tts   (added to requirements.txt)
"""
from pathlib import Path


def synthesize_to_file(text: str, voice: str, out_path: str) -> bool:
    import asyncio

    import edge_tts

    async def _run():
        comm = edge_tts.Communicate(text, voice)
        await comm.save(out_path)

    try:
        asyncio.run(_run())
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[tts] failed for voice={voice}: {e}", flush=True)
        return False


def generate_voiceover(scenes: list[str], voice_ids: list[str], out_dir: Path) -> list[str]:
    """Synthesize one mp3 per scene. Returns the list of written mp3 paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for i, scene in enumerate(scenes):
        voice = voice_ids[i % len(voice_ids)] if voice_ids else "en-US-GuyNeural"
        text = (scene or "").strip()
        path = out_dir / f"scene_{i}.mp3"
        if not text:
            print(f"[tts] scene {i} empty, skipping", flush=True)
            continue
        ok = synthesize_to_file(text, voice, str(path))
        if ok:
            written.append(str(path))
            print(f"[tts] scene {i} -> {voice} ({path.name})", flush=True)
    return written
