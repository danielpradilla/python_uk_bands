export const DASHBOARD_DATA_URL = "/data/dashboard.json";
export const UK_OUTLINE_URL = "/data/uk-outline.geojson";

export function resolveAssetUrl(stableUrl, basePath = "") {
  const base = basePath.replace(/\/$/, "");
  return `${base}${stableUrl}`;
}

export function assetUrl(stableUrl) {
  const basePath = document.querySelector('meta[name="asset-base"]')?.content || "";
  return resolveAssetUrl(stableUrl, basePath);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load ${url} (${response.status})`);
  }
  return response.json();
}

export async function loadExplorerData() {
  const [dashboard, outline] = await Promise.all([
    fetchJson(assetUrl(DASHBOARD_DATA_URL)),
    fetchJson(assetUrl(UK_OUTLINE_URL)),
  ]);
  return { dashboard, outline };
}
