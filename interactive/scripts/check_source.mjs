import { execFile } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import path from "node:path";

const exec = promisify(execFile);
const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceFiles = (await readdir(path.join(projectDir, "src")))
  .filter((name) => name.endsWith(".js"))
  .map((name) => path.join(projectDir, "src", name));
const scriptFiles = [
  path.join(projectDir, "scripts", "build_frontend.mjs"),
  path.join(projectDir, "scripts", "check_source.mjs"),
];

for (const file of [...sourceFiles, ...scriptFiles]) {
  await exec(process.execPath, ["--check", file]);
}

const browserSource = await Promise.all(sourceFiles.map((file) => readFile(file, "utf8")));
const combined = browserSource.join("\n");
if (/https?:\/\/[^"'`\s]+\.(?:png|jpg|svg|js|css)/i.test(combined)) {
  throw new Error("Browser source must not load runtime assets from third parties");
}
if (/stadia|openstreetmap\.org\/\{z\}|tilelayer/i.test(combined)) {
  throw new Error("Explorer must use its bundled outline rather than runtime tiles");
}
console.log(`${sourceFiles.length + scriptFiles.length} JavaScript files checked`);
