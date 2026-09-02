export const DEFAULT_METRIC = "monthly_listeners";
export const METRICS = new Set(["monthly_listeners", "followers"]);
export const DEFAULT_COMPARISON = "raw";
export const COMPARISONS = new Set(["raw", "population_normalized"]);

export function parseExplorerState(search, dashboard) {
  const params = new URLSearchParams(search);
  const bandsById = new Map(dashboard.bands.map((band) => [band.id, band]));
  const placesById = new Map(dashboard.places.map((place) => [place.id, place]));
  const fuasById = new Map(dashboard.fuas.map((fua) => [fua.id, fua]));
  const band = bandsById.get(params.get("band")) || null;
  const explicitPlace = placesById.get(params.get("place")) || null;
  const explicitFua = fuasById.get(params.get("fua")) || null;
  const metric = METRICS.has(params.get("metric")) ? params.get("metric") : DEFAULT_METRIC;
  const comparison = COMPARISONS.has(params.get("comparison"))
    ? params.get("comparison")
    : DEFAULT_COMPARISON;

  let selectedOrigin = explicitPlace?.id || null;
  if (!selectedOrigin && band?.originCluster) selectedOrigin = band.originCluster;
  let selectedFua = explicitFua?.id || null;
  if (!selectedFua && band?.fuaCode) selectedFua = band.fuaCode;
  if (!selectedFua && selectedOrigin) selectedFua = placesById.get(selectedOrigin)?.fuaCode || null;

  return {
    selectedBandId: band?.id || null,
    selectedOrigin,
    selectedFua,
    metric,
    comparison,
  };
}

export function updateUrl(state, mode = "replace") {
  const url = new URL(window.location.href);
  url.search = "";
  if (state.selectedBandId) url.searchParams.set("band", state.selectedBandId);
  if (state.comparison === "population_normalized") {
    if (state.selectedFua) url.searchParams.set("fua", state.selectedFua);
  } else if (state.selectedOrigin) {
    url.searchParams.set("place", state.selectedOrigin);
  }
  if (state.metric !== DEFAULT_METRIC) url.searchParams.set("metric", state.metric);
  if (state.comparison !== DEFAULT_COMPARISON) {
    url.searchParams.set("comparison", state.comparison);
  }
  const method = mode === "push" ? "pushState" : "replaceState";
  window.history[method](null, "", url);
}
