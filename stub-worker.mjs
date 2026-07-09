// GPU-free demo worker (pure Node + ffmpeg). It simulates the full generation
// lifecycle so you can see the UI/API working before setting up Python models.
//
//   npm run dev         (terminal 1)
//   npm run stub-worker (terminal 2)
//
// It mirrors python/main.py's stub path: watches .jobs/queue, writes status
// progress, produces ffmpeg test clips, stitches them, and emits final.mp4.
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const QUEUE = path.join(root, ".jobs", "queue");
const ACTIVE = path.join(root, ".jobs", "active");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function ff(args) {
  const r = spawnSync("ffmpeg", ["-y", ...args], { stdio: "ignore" });
  return r.status === 0;
}

function splitScenes(script) {
  const text = (script || "").trim();
  if (!text) return [];
  const explicit = text.split(/\r?\n/).some((l) => /^scene\s*:/i.test(l.trim()));
  if (explicit) {
    const parts = text.split(/^\s*scene\s*:\s*/gim).slice(1).map((s) => s.trim()).filter(Boolean);
    if (parts.length) return parts;
  }
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  if (blocks.length > 1) return blocks;
  const sents = text.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean);
  if (sents.length <= 1) return [text];
  const out = [];
  for (let i = 0; i < sents.length; i += 2) out.push(sents.slice(i, i + 2).join(" "));
  return out;
}

function main() {
  mkdirSync(QUEUE, { recursive: true });
  mkdirSync(ACTIVE, { recursive: true });
  writeFileSync(path.join(root, ".jobs", ".mode"), "stub");

  const files = readdirSync(QUEUE).filter((f) => f.endsWith(".json")).sort();
  if (files.length === 0) return false;

  const file = files[0];
  let data;
  try {
    data = JSON.parse(readFileSync(path.join(QUEUE, file), "utf8"));
  } catch {
    unlinkSync(path.join(QUEUE, file));
    return true;
  }
  const jobId = data.id;
  unlinkSync(path.join(QUEUE, file));

  const jobdir = path.join(ACTIVE, jobId);
  mkdirSync(jobdir, { recursive: true });
  writeFileSync(path.join(jobdir, "request.json"), JSON.stringify(data, null, 2));

  const req = data.request || {};
  const opts = req.options || {};
  const res = opts.resolution || "480p";
  const ratio = opts.ratio || "16:9";
  const secs = Number(opts.secondsPerScene) || 4;
  const voiceover = Boolean(opts.voiceover);
  const [W, H] = ratio === "9:16"
    ? (res === "720p" ? [720, 1280] : [480, 854])
    : (res === "720p" ? [1280, 720] : [854, 480]);
  const fps = Math.max(6, Math.round(25 / secs));

  const base = {
    id: jobId,
    style: req.style || "cinematic",
    status: "processing",
    stage: "script",
    progress: 3,
    sceneTotal: 0,
    sceneDone: 0,
    createdAt: data.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    error: null,
    output: null,
    request: req,
  };
  const write = (fields) => {
    Object.assign(base, fields);
    base.updatedAt = new Date().toISOString();
    writeFileSync(path.join(jobdir, "status.json"), JSON.stringify(base, null, 2));
  };

  const scenes = splitScenes(req.script);
  const total = Math.max(1, scenes.length);
  write({ status: "processing", sceneTotal: total, sceneDone: 0, progress: 5 });

  const audioDir = path.join(jobdir, "audio");
  if (voiceover) mkdirSync(audioDir, { recursive: true });

  for (let i = 0; i < total; i++) {
    write({ stage: "images", sceneDone: i, progress: 5 + Math.round(35 * (i + 0.5) / total) });
    if (!ff(["-f", "lavfi", "-i", `testsrc=size=${W}x${H}:rate=${fps}:duration=${secs}`, "-pix_fmt", "yuv420p", path.join(jobdir, `scene_${i}.mp4`)])) {
      write({ status: "error", stage: "done", error: "ffmpeg failed to create scene", progress: 100 });
      return true;
    }
    if (voiceover) {
      ff(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", String(secs),
          "-acodec", "libmp3lame", path.join(audioDir, `scene_${i}.mp3`)]);
    }
    write({ stage: "animating", sceneDone: i + 1, progress: 5 + Math.round(80 * (i + 1) / total) });
    sleep(250);
  }

  write({ stage: "stitching", progress: 92 });
  // When voice-over is on, mux silence into each clip so the final has an audio track.
  if (voiceover) {
    for (let i = 0; i < total; i++) {
      const v = path.join(jobdir, `scene_${i}.mp4`);
      const a = path.join(audioDir, `scene_${i}.mp3`);
      ff(["-i", v, "-i", a, "-filter_complex", "[1:a]anull[outa]", "-map", "0:v", "-map", "[outa]",
          "-c:v", "copy", "-c:a", "aac", "-shortest", path.join(jobdir, `scene_${i}_v.mp4`)]);
    }
  }
  const list = scenes.map((_, i) => {
    const v = voiceover ? path.join(jobdir, `scene_${i}_v.mp4`) : path.join(jobdir, `scene_${i}.mp4`);
    return `file '${v.replace(/\\/g, "/")}'`;
  }).join("\n");
  writeFileSync(path.join(jobdir, "concat.txt"), list);
  if (!ff(["-f", "concat", "-safe", "0", "-i", path.join(jobdir, "concat.txt"), "-c", "copy", path.join(jobdir, "pre.mp4")])) {
    write({ status: "error", stage: "done", error: "ffmpeg concat failed", progress: 100 });
    return true;
  }
  const pre = path.join(jobdir, "pre.mp4");
  const final = path.join(jobdir, "final.mp4");
  if (existsSync(final)) unlinkSync(final);
  renameSync(pre, final);

  ff(["-f", "lavfi", "-i", `testsrc=size=${W}x${H}:rate=1:duration=1`, "-frames:v", "1", path.join(jobdir, "poster.png")]);

  write({ stage: "done", status: "done", progress: 100, output: "final.mp4" });
  return true;
}

async function loop() {
  console.log("[stub-worker] watching .jobs/queue (GPU-free demo mode)…");
  while (true) {
    try {
      main();
    } catch (e) {
      console.error("[stub-worker] error:", e);
    }
    await sleep(1500);
  }
}
loop();
