// Bootstraps a Python 3.11/3.12 venv with PyTorch (CUDA) + the ML deps.
// Usage: npm run setup   (optionally: npm run setup --prefetch)
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const venvDir = path.join(root, "python", ".venv");
const prefetch = process.argv.includes("--prefetch");

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: "inherit", cwd: root, ...opts });
  if (r.status !== 0) {
    console.error(`\n✗ Command failed: ${cmd} ${args.join(" ")}`);
    process.exit(1);
  }
}

function findPython() {
  const candidates = [
    "py -3.11", "py -3.12",
    "python3.11", "python3.12",
    "py -3", "python3",
  ];
  for (const c of candidates) {
    const [exe, ...rest] = c.split(" ");
    const r = spawnSync(exe, [...rest, "-c", "import sys;print(sys.version_info[:2])"], {
      encoding: "utf8",
    });
    if (r.status !== 0 || !r.stdout) continue;
    const m = r.stdout.trim().match(/\((\d+),\s*(\d+)\)/);
    if (!m) continue;
    const major = Number(m[1]);
    const minor = Number(m[2]);
    if (major === 3 && minor >= 11 && minor <= 12) {
      return c;
    }
  }
  return null;
}

console.log("🔍 Looking for Python 3.11/3.12 …");
const py = findPython();
if (!py) {
  console.error(
    "\n✗ Could not find Python 3.11 or 3.12.\n" +
      "  CineForge's generation models (PyTorch/Diffusers) do not support the\n" +
      "  Python 3.14 that is currently on PATH. Please install Python 3.11 or 3.12\n" +
      "  from https://www.python.org/downloads/ and re-run: npm run setup\n"
  );
  process.exit(1);
}
console.log(`✓ Using: ${py}`);

console.log("\n📦 Creating venv …");
run(py, ["-m", "venv", venvDir]);

const vpy = process.platform === "win32"
  ? path.join(venvDir, "Scripts", "python.exe")
  : path.join(venvDir, "bin", "python");

console.log("\n⬆️  Upgrading pip …");
run(vpy, ["-m", "pip", "install", "--upgrade", "pip"]);

console.log("\n🧠 Installing PyTorch (CUDA 12.4) — this is large …");
run(vpy, [
  "-m", "pip", "install",
  "torch==2.5.1", "torchvision==0.20.1",
  "--index-url", "https://download.pytorch.org/whl/cu124",
]);

console.log("\n📚 Installing ML dependencies …");
run(vpy, ["-m", "pip", "install", "-r", "python/requirements.txt"]);

if (prefetch) {
  console.log("\n⬇️  Pre-downloading model weights …");
  run(vpy, ["python/main.py", "prefetch"]);
}

console.log(
  "\n✅ Setup complete!\n" +
    "   Start the site:   npm run dev\n" +
    "   Start the worker: npm run worker   (in another terminal)\n"
);
