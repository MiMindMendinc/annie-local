import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { delimiter, resolve } from "node:path";

const portable = resolve(".preview-python/bin/python");
const python = existsSync(portable) ? portable : resolve(process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const runtime = existsSync(portable) ? JSON.parse(readFileSync(resolve(".preview-python/runtime.json"), "utf8")) : null;
if (!existsSync(python)) {
  throw new Error("Create .venv and install Annie in it before running the UI preview. See docs/TODAY_WORKSPACE.md.");
}
const children = new Set();
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill("SIGTERM");
  process.exitCode = code;
  const forceStop = setTimeout(() => {
    for (const child of children) child.kill("SIGKILL");
  }, 3000);
  forceStop.unref();
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());

const api = spawn(python, ["-m", "uvicorn", "annie.server:create_app", "--factory", "--host", "127.0.0.1", "--port", "18787"], {
  env: {
    ...process.env,
    ANNIE_MODE: "local",
    AUTH_DISABLED: "true",
    ANNIE_DATA_DIR: resolve(".annie-preview"),
    ...(runtime ? {
      PYTHONPATH: [resolve("src"), resolve(runtime.sitePackages)].join(delimiter),
      LD_LIBRARY_PATH: [resolve(".preview-python/lib"), process.env.LD_LIBRARY_PATH].filter(Boolean).join(delimiter),
    } : {}),
  },
  stdio: ["ignore", "pipe", "pipe"],
});
children.add(api);
api.on("exit", (code) => { children.delete(api); stop(code || 0); });
api.on("error", (error) => { console.error(error.message); stop(1); });

try {
  await new Promise((resolveReady, reject) => {
    const timeout = setTimeout(() => reject(new Error("Annie preview API did not start within 20 seconds.")), 20000);
    api.on("error", (error) => { clearTimeout(timeout); reject(error); });
    api.on("exit", () => { clearTimeout(timeout); reject(new Error("Annie preview API exited before startup.")); });
    let startupLog = "";
    const output = (chunk) => {
      process.stderr.write(chunk);
      startupLog = (startupLog + String(chunk)).slice(-4000);
      if (startupLog.includes("Uvicorn running on http://127.0.0.1:18787")) {
        clearTimeout(timeout);
        resolveReady();
      }
    };
    api.stdout.on("data", output);
    api.stderr.on("data", output);
  });
  if (!stopping) {
    const vite = spawn(process.execPath, [resolve("node_modules/vite/bin/vite.js"), ...process.argv.slice(2)], { stdio: "inherit" });
    children.add(vite);
    vite.on("exit", (code) => { children.delete(vite); stop(code || 0); });
    vite.on("error", (error) => { console.error(error.message); stop(1); });
  }
} catch (error) {
  console.error(error.message);
  stop(1);
}
