import { createHash } from "node:crypto";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = path.join(projectDir, "dist");
const sourceDir = path.join(projectDir, "src");
const publicBase = (process.env.PUBLIC_BASE || "").replace(/\/$/, "");
if (publicBase && !/^\/[a-z0-9/_-]+$/i.test(publicBase)) {
  throw new Error("PUBLIC_BASE must be an origin-relative path such as /uk-music-cities");
}

const sourceNames = (await readdir(sourceDir)).sort();
const versionHash = createHash("sha256");
versionHash.update(await readFile(path.join(projectDir, "index.html")));
for (const name of sourceNames) {
  versionHash.update(name);
  versionHash.update(await readFile(path.join(sourceDir, name)));
}
const assetVersion = versionHash.digest("hex").slice(0, 12);

await rm(outputDir, { recursive: true, force: true });
await mkdir(outputDir, { recursive: true });
await cp(sourceDir, path.join(outputDir, "src"), { recursive: true });
await cp(path.join(projectDir, "public"), outputDir, { recursive: true });
await cp(path.join(projectDir, "index.html"), path.join(outputDir, "index.html"));

for (const name of sourceNames.filter((entry) => entry.endsWith(".js"))) {
  const outputPath = path.join(outputDir, "src", name);
  const source = await readFile(outputPath, "utf8");
  const versionedSource = source.replace(
    /(from\s+["'])(\.\/[^"'?]+\.js)(["'])/g,
    `$1$2?v=${assetVersion}$3`,
  );
  await writeFile(outputPath, versionedSource, "utf8");
}

let html = await readFile(path.join(outputDir, "index.html"), "utf8");
if (/https?:\/\/[^"']+\.(?:js|css)/i.test(html)) {
  throw new Error("Production HTML must not load scripts or styles from a CDN");
}
html = html.replace(
  /((?:href|src)="\/src\/[^"?]+\.(?:js|css))"/g,
  `$1?v=${assetVersion}"`,
);
if (publicBase) {
  html = html
    .replace('name="asset-base" content=""', `name="asset-base" content="${publicBase}"`)
    .replaceAll('href="/src/', `href="${publicBase}/src/`)
    .replaceAll('src="/src/', `src="${publicBase}/src/`);
}
if (!html.includes(`/src/main.js?v=${assetVersion}`)
    || !html.includes(`/src/styles.css?v=${assetVersion}`)) {
  throw new Error("Production browser assets must carry the build content version");
}
await writeFile(path.join(outputDir, "index.html"), html, "utf8");
await writeFile(path.join(outputDir, ".nojekyll"), "", "utf8");
console.log(`${path.relative(process.cwd(), path.join(outputDir, "index.html"))} (${assetVersion})`);
