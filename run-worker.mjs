// Spawns the Python generation worker using the project venv.
// Usage: npm run worker   (add --stub to simulate without a GPU)
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
const vpy = process.platform === "win32"
  ? path.join(root, "python", ".venv", "Scripts", "python.exe")
  : path.join(root, "python", ".venv", "bin", "python");

import { existsSync } from "node:fs";
if (!existsSync(vpy)) {
  console.error(
    "✗ Python venv not found. Run `npm run setup` first (needs Python 3.11/3.12)."
  );
  process.exit(1);
}

const child = spawn(vpy, ["python/main.py", ...process.argv.slice(2)], {
  cwd: root,
  stdio: "inherit",
});
child.on("exit", (code) => process.exit(code ?? 0));
