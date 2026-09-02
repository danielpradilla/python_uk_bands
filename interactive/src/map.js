const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 760;
const HEIGHT = 620;
const PADDING = 30;
const ZOOM_STEP = 1.35;
export const DEFAULT_MAP_ZOOM = ZOOM_STEP ** 2;
const DEFAULT_TRANSLATE_X = (WIDTH * (1 - DEFAULT_MAP_ZOOM)) / 2;
const DEFAULT_TRANSLATE_Y = HEIGHT - (HEIGHT - PADDING) * DEFAULT_MAP_ZOOM;
const MIN_BUBBLE_RADIUS = 4;
const MAX_BUBBLE_RADIUS = 24;
const MAP_LABEL_FONT_SIZE = 8.5;
export const MAP_LABEL_PLACE_IDS = Object.freeze([
  "London",
  "Manchester",
  "Liverpool",
  "Birmingham",
  "Glasgow",
  "Edinburgh",
  "Cardiff",
  "Belfast",
]);
const MAP_LABEL_OFFSETS = {
  Belfast: { x: -10, y: -8, anchor: "end" },
  Birmingham: { x: 10, y: 13, anchor: "start" },
  Cardiff: { x: -10, y: 13, anchor: "end" },
  Edinburgh: { x: 10, y: 13, anchor: "start" },
  Glasgow: { x: -10, y: -8, anchor: "end" },
  Liverpool: { x: -10, y: 12, anchor: "end" },
  London: { x: 11, y: -8, anchor: "start" },
  Manchester: { x: 10, y: -9, anchor: "start" },
};
const integerFormat = new Intl.NumberFormat("en-GB");
const compactFormat = new Intl.NumberFormat("en-GB", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const decimalFormat = new Intl.NumberFormat("en-GB", {
  maximumFractionDigits: 1,
});

export function placeMetricValue(place, metric, comparison = "raw") {
  if (comparison === "population_normalized") {
    return metric === "followers"
      ? place.followersPerResident
      : place.monthlyListenersPerResident;
  }
  return metric === "followers" ? place.followersTotal : place.monthlyListenersTotal;
}

export function sharedMetricMaximum(places, comparison = "raw") {
  return Math.max(
    ...places
      .filter((place) => place.locationStatus === "uk")
      .flatMap((place) => comparison === "population_normalized"
        ? [place.monthlyListenersPerResident, place.followersPerResident]
        : [place.monthlyListenersTotal, place.followersTotal]),
    1,
  );
}

export function markerRadius(value, maxValue) {
  if (!Number.isFinite(value) || value <= 0 || !Number.isFinite(maxValue) || maxValue <= 0) {
    return MIN_BUBBLE_RADIUS;
  }
  return MIN_BUBBLE_RADIUS
    + (MAX_BUBBLE_RADIUS - MIN_BUBBLE_RADIUS) * Math.sqrt(Math.min(1, value / maxValue));
}

export function pointerPairGesture(points) {
  if (points.length < 2) return null;
  const [first, second] = points;
  return {
    center: {
      x: (first.x + second.x) / 2,
      y: (first.y + second.y) / 2,
    },
    distance: Math.hypot(second.x - first.x, second.y - first.y),
  };
}

export function rectangleBounds(start, end) {
  return {
    minX: Math.min(start.x, end.x),
    maxX: Math.max(start.x, end.x),
    minY: Math.min(start.y, end.y),
    maxY: Math.max(start.y, end.y),
  };
}

export function pointInBounds(point, bounds) {
  return point.x >= bounds.minX
    && point.x <= bounds.maxX
    && point.y >= bounds.minY
    && point.y <= bounds.maxY;
}

function element(name, attributes = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

function geometryCoordinates(geometry) {
  if (geometry.type === "Polygon") return geometry.coordinates;
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
  throw new Error(`Unsupported map geometry: ${geometry.type}`);
}

function createProjection(outline) {
  const points = outline.features.flatMap((feature) =>
    geometryCoordinates(feature.geometry).flat(),
  );
  const mercator = ([longitude, latitude]) => {
    const x = (longitude * Math.PI) / 180;
    const clamped = Math.max(-85, Math.min(85, latitude));
    const y = -Math.log(Math.tan(Math.PI / 4 + (clamped * Math.PI) / 360));
    return [x, y];
  };
  const projected = points.map(mercator);
  const xs = projected.map(([x]) => x);
  const ys = projected.map(([, y]) => y);
  const bounds = {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
  const scale = Math.min(
    (WIDTH - PADDING * 2) / (bounds.maxX - bounds.minX),
    (HEIGHT - PADDING * 2) / (bounds.maxY - bounds.minY),
  );
  const offsetX = (WIDTH - (bounds.maxX - bounds.minX) * scale) / 2;
  const offsetY = (HEIGHT - (bounds.maxY - bounds.minY) * scale) / 2;
  return ([longitude, latitude]) => {
    const [x, y] = mercator([longitude, latitude]);
    return [
      offsetX + (x - bounds.minX) * scale,
      offsetY + (y - bounds.minY) * scale,
    ];
  };
}

function featurePath(feature, project) {
  return geometryCoordinates(feature.geometry)
    .map((ring) =>
      ring
        .map((coordinate, index) => {
          const [x, y] = project(coordinate);
          return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" ") + " Z",
    )
    .join(" ");
}

export class BandMap {
  constructor(container, outline, dashboard, onSelect, onAreaSelect) {
    this.container = container;
    this.dashboard = dashboard;
    this.onSelect = onSelect;
    this.onAreaSelect = onAreaSelect || (() => {});
    this.project = createProjection(outline);
    this.metric = "monthly_listeners";
    this.comparison = "raw";
    this.places = [];
    this.selectedPlace = null;
    this.zoom = DEFAULT_MAP_ZOOM;
    this.translateX = DEFAULT_TRANSLATE_X;
    this.translateY = DEFAULT_TRANSLATE_Y;
    this.pointers = new Map();
    this.areaSelectionMode = false;
    this.areaDrag = null;
    this.areaPlaceIds = new Set();
    this.suppressMarkerClick = false;
    this.bandById = new Map(dashboard.bands.map((band) => [band.id, band]));
    this.metricMax = 1;

    this.svg = element("svg", {
      class: "uk-map",
      viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
      role: "group",
      "aria-labelledby": "map-title",
      "aria-describedby": "map-description",
    });
    const title = element("title", { id: "map-title" });
    title.textContent = "United Kingdom music geography map";
    this.description = element("desc", { id: "map-description" });
    this.svg.append(title, this.description);

    this.viewport = element("g", { class: "map-viewport" });
    const outlineLayer = element("g", { class: "outline-layer" });
    outline.features.forEach((feature) => {
      outlineLayer.append(
        element("path", {
          class: "uk-outline",
          d: featurePath(feature, this.project),
          "fill-rule": "evenodd",
        }),
      );
    });
    this.areaLayer = element("g", { class: "map-area-layer", "aria-hidden": "true" });
    this.areaSelectionRect = element("rect", {
      class: "map-area-selection",
      "vector-effect": "non-scaling-stroke",
    });
    this.areaLayer.append(this.areaSelectionRect);
    this.markerLayer = element("g", { class: "marker-layer" });
    this.labelLayer = element("g", { class: "map-label-layer", "aria-hidden": "true" });
    this.viewport.append(outlineLayer, this.areaLayer, this.markerLayer, this.labelLayer);
    this.svg.append(this.viewport);
    this.container.append(this.svg);

    this.tooltip = document.createElement("div");
    this.tooltip.className = "map-tooltip";
    this.tooltip.hidden = true;
    this.tooltip.setAttribute("role", "tooltip");
    this.container.append(this.tooltip);

    this.legend = document.createElement("div");
    this.legend.className = "map-bubble-legend";
    this.legend.setAttribute("role", "note");
    this.legendScale = document.createElement("div");
    this.legendScale.className = "bubble-legend-scale";
    this.legend.append(this.legendScale);
    this.container.append(this.legend);

    this.markers = new Map();
    this.labels = new Map();
    this.bindPanAndZoom();
    this.setPlaces(dashboard.places, "raw");
  }

  setPlaces(places, comparison) {
    if (this.places === places && this.comparison === comparison) return;
    this.cancelAreaSelection();
    this.areaPlaceIds.clear();
    this.areaSelectionRect.classList.remove("is-visible");
    this.markerLayer.replaceChildren();
    this.labelLayer.replaceChildren();
    this.markers.clear();
    this.labels.clear();
    this.places = places;
    this.comparison = comparison;
    this.selectedPlace = null;
    this.metricMax = sharedMetricMaximum(places, comparison);
    places
      .filter((place) => place.locationStatus === "uk")
      .forEach((place) => {
        this.addMarker(place);
        this.addLabel(place);
      });
    this.description.textContent = comparison === "population_normalized"
      ? `Interactive map of ${places.length} OECD Functional Urban Areas. Bubble size is the mapped catalog's active Spotify total divided by 2024 FUA population.`
      : "Interactive map of reviewed formation places. Bubble size increases with the active place-level Spotify total on a shared count scale.";
    this.setMetric(this.metric);
  }

  addMarker(place) {
    const [x, y] = this.project([place.longitude, place.latitude]);
    const group = element("g", {
      class: "map-marker",
      tabindex: "0",
      role: "button",
      "data-place": place.id,
      transform: `translate(${x},${y})`,
    });
    const hit = element("circle", { class: "marker-hit", r: "10" });
    const dot = element("circle", { class: "marker-dot", r: String(MIN_BUBBLE_RADIUS) });
    const ring = element("circle", { class: "marker-ring", r: "6" });
    const tick = element("path", {
      class: "marker-tick",
      d: "M-2.7,0 L-0.7,2.2 L3.2,-2.6",
      "vector-effect": "non-scaling-stroke",
    });
    group.append(hit, dot, ring, tick);
    group.addEventListener("click", () => {
      if (this.areaSelectionMode || this.suppressMarkerClick) return;
      this.onSelect(place.id);
    });
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this.onSelect(place.id);
      }
    });
    group.addEventListener("pointerenter", () => this.showTooltip(place));
    group.addEventListener("pointerleave", () => this.hideTooltip());
    group.addEventListener("focus", () => this.showTooltip(place));
    group.addEventListener("blur", () => this.hideTooltip());
    this.markerLayer.append(group);
    this.markers.set(place.id, { group, hit, dot, ring, place, x, y });
    this.updateMarkerLabel(place.id);
  }

  addLabel(place) {
    const marker = this.markers.get(place.id);
    const offset = MAP_LABEL_OFFSETS[place.label] || { x: 10, y: -8, anchor: "start" };
    const group = element("g", {
      class: `map-city-label${MAP_LABEL_PLACE_IDS.includes(place.label) ? " is-base" : ""}`,
      transform: `translate(${marker.x},${marker.y})`,
    });
    const text = element("text", {
      x: String(offset.x),
      y: String(offset.y),
      "text-anchor": offset.anchor,
    });
    text.textContent = place.label;
    group.append(text);
    this.labelLayer.append(group);
    this.labels.set(place.id, { group, text, offset });
  }

  mapPoint(point) {
    return {
      x: (point.x - this.translateX) / this.zoom,
      y: (point.y - this.translateY) / this.zoom,
    };
  }

  updateAreaRectangle(start, end) {
    const bounds = rectangleBounds(start, end);
    this.areaSelectionRect.setAttribute("x", String(bounds.minX));
    this.areaSelectionRect.setAttribute("y", String(bounds.minY));
    this.areaSelectionRect.setAttribute("width", String(bounds.maxX - bounds.minX));
    this.areaSelectionRect.setAttribute("height", String(bounds.maxY - bounds.minY));
    this.areaSelectionRect.classList.add("is-visible");
    return bounds;
  }

  startAreaSelection() {
    this.areaSelectionMode = true;
    this.svg.classList.add("is-area-selecting");
    this.hideTooltip();
  }

  cancelAreaSelection() {
    this.areaSelectionMode = false;
    this.areaDrag = null;
    this.svg.classList.remove("is-area-selecting");
    if (!this.areaPlaceIds.size) this.areaSelectionRect.classList.remove("is-visible");
  }

  clearAreaSelection() {
    this.cancelAreaSelection();
    this.areaPlaceIds.clear();
    this.areaSelectionRect.classList.remove("is-visible");
    this.markers.forEach(({ group }) => group.classList.remove("is-area-selected"));
  }

  completeAreaSelection() {
    const drag = this.areaDrag;
    if (!drag) return;
    const moved = Math.hypot(
      drag.currentSvg.x - drag.startSvg.x,
      drag.currentSvg.y - drag.startSvg.y,
    );
    if (moved < 5) {
      this.cancelAreaSelection();
      return;
    }
    const bounds = this.updateAreaRectangle(drag.startMap, drag.currentMap);
    const placeIds = [...this.markers.values()]
      .filter((marker) => pointInBounds(marker, bounds))
      .map((marker) => marker.place.id);
    this.areaPlaceIds = new Set(placeIds);
    this.markers.forEach(({ group }, placeId) => {
      group.classList.toggle("is-area-selected", this.areaPlaceIds.has(placeId));
    });
    this.areaDrag = null;
    this.areaSelectionMode = false;
    this.svg.classList.remove("is-area-selecting");
    this.suppressMarkerClick = true;
    window.setTimeout(() => {
      this.suppressMarkerClick = false;
    }, 0);
    this.onAreaSelect(placeIds);
  }

  bindPanAndZoom() {
    this.svg.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const point = this.svgPoint(event.clientX, event.clientY);
        this.zoomAt(event.deltaY < 0 ? 1.22 : 1 / 1.22, point.x, point.y);
      },
      { passive: false },
    );
    this.svg.addEventListener("pointerdown", (event) => {
      if (this.areaSelectionMode) {
        event.preventDefault();
        this.svg.setPointerCapture(event.pointerId);
        const startSvg = this.svgPoint(event.clientX, event.clientY);
        const startMap = this.mapPoint(startSvg);
        this.areaDrag = {
          pointerId: event.pointerId,
          startSvg,
          currentSvg: startSvg,
          startMap,
          currentMap: startMap,
        };
        this.updateAreaRectangle(startMap, startMap);
        return;
      }
      const marker = event.target.closest(".map-marker");
      if (event.pointerType !== "touch" && marker) return;
      if (!marker) this.svg.setPointerCapture(event.pointerId);
      this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      this.svg.classList.add("is-panning");
    });
    this.svg.addEventListener("pointermove", (event) => {
      if (this.areaDrag?.pointerId === event.pointerId) {
        const currentSvg = this.svgPoint(event.clientX, event.clientY);
        this.areaDrag.currentSvg = currentSvg;
        this.areaDrag.currentMap = this.mapPoint(currentSvg);
        this.updateAreaRectangle(this.areaDrag.startMap, this.areaDrag.currentMap);
        return;
      }
      const previous = this.pointers.get(event.pointerId);
      if (!previous) return;
      const previousGesture = pointerPairGesture([...this.pointers.values()]);
      this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      const currentGesture = pointerPairGesture([...this.pointers.values()]);
      if (previousGesture && currentGesture) {
        const previousCenter = this.svgPoint(
          previousGesture.center.x,
          previousGesture.center.y,
        );
        const currentCenter = this.svgPoint(
          currentGesture.center.x,
          currentGesture.center.y,
        );
        this.translateX += currentCenter.x - previousCenter.x;
        this.translateY += currentCenter.y - previousCenter.y;
        const factor = previousGesture.distance > 0
          ? currentGesture.distance / previousGesture.distance
          : 1;
        this.zoomAt(factor, currentCenter.x, currentCenter.y);
        return;
      }

      const previousPoint = this.svgPoint(previous.x, previous.y);
      const currentPoint = this.svgPoint(event.clientX, event.clientY);
      this.translateX += currentPoint.x - previousPoint.x;
      this.translateY += currentPoint.y - previousPoint.y;
      this.applyTransform();
    });
    const finish = (event) => {
      if (this.areaDrag?.pointerId === event.pointerId) {
        this.completeAreaSelection();
        return;
      }
      this.pointers.delete(event.pointerId);
      if (this.pointers.size === 0) this.svg.classList.remove("is-panning");
    };
    this.svg.addEventListener("pointerup", finish);
    this.svg.addEventListener("pointercancel", (event) => {
      if (this.areaDrag?.pointerId === event.pointerId) this.cancelAreaSelection();
      finish(event);
    });
    this.svg.addEventListener("lostpointercapture", finish);
  }

  svgPoint(clientX, clientY) {
    const point = this.svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    return point.matrixTransform(this.svg.getScreenCTM().inverse());
  }

  zoomAt(factor, x = WIDTH / 2, y = HEIGHT / 2) {
    const oldZoom = this.zoom;
    this.zoom = Math.max(1, Math.min(7, this.zoom * factor));
    const ratio = this.zoom / oldZoom;
    this.translateX = x - (x - this.translateX) * ratio;
    this.translateY = y - (y - this.translateY) * ratio;
    this.applyTransform();
  }

  zoomIn() {
    this.zoomAt(ZOOM_STEP);
  }

  zoomOut() {
    this.zoomAt(1 / ZOOM_STEP);
  }

  reset() {
    this.zoom = DEFAULT_MAP_ZOOM;
    this.translateX = DEFAULT_TRANSLATE_X;
    this.translateY = DEFAULT_TRANSLATE_Y;
    this.applyTransform();
  }

  focusPlace(placeId) {
    const marker = this.markers.get(placeId);
    if (!marker) return;
    this.zoom = Math.max(this.zoom, 2.35);
    this.translateX = WIDTH / 2 - marker.x * this.zoom;
    this.translateY = HEIGHT / 2 - marker.y * this.zoom;
    this.applyTransform();
  }

  setSelection(placeId, focus = false) {
    this.selectedPlace = placeId;
    this.markers.forEach(({ group }, id) => {
      group.classList.toggle("is-selected", id === placeId);
      group.setAttribute("aria-pressed", String(id === placeId));
    });
    const selected = this.markers.get(placeId);
    if (selected) this.markerLayer.append(selected.group);
    this.labels.forEach(({ group }, id) => {
      group.classList.toggle("is-selected", id === placeId);
    });
    const selectedLabel = this.labels.get(placeId);
    if (selectedLabel) this.labelLayer.append(selectedLabel.group);
    if (focus) this.focusPlace(placeId);
  }

  setMetric(metric) {
    this.metric = metric;
    this.markers.forEach((_, placeId) => this.updateMarkerLabel(placeId));
    this.refreshMarkerPresentation();
    this.renderLegend();
    this.hideTooltip();
  }

  metricDetails(place) {
    const baseLabel = this.metric === "followers" ? "followers" : "monthly listeners";
    const value = placeMetricValue(place, this.metric, this.comparison);
    const normalized = this.comparison === "population_normalized";
    return {
      label: normalized
        ? `normalized ${baseLabel}`
        : `total ${baseLabel}`,
      accessibleLabel: normalized
        ? `population-normalized ${baseLabel}`
        : `total ${baseLabel}`,
      value,
      formattedValue: normalized
        ? decimalFormat.format(value)
        : integerFormat.format(value),
    };
  }

  refreshMarkerPresentation() {
    this.applyTransform();
    [...this.markers.values()]
      .sort((a, b) =>
        placeMetricValue(b.place, this.metric, this.comparison)
          - placeMetricValue(a.place, this.metric, this.comparison)
        || a.place.label.localeCompare(b.place.label),
      )
      .forEach(({ group }) => this.markerLayer.append(group));
    const selected = this.markers.get(this.selectedPlace);
    if (selected) this.markerLayer.append(selected.group);
  }

  renderLegend() {
    this.legendScale.replaceChildren();
    const metricLabel = this.metric === "followers" ? "followers" : "monthly listeners";
    const title = document.createElement("strong");
    title.textContent = this.comparison === "population_normalized"
      ? `Normalized ${metricLabel} · shared scale`
      : `Place total ${metricLabel} · shared scale`;
    const values = [0.01, 0.25, 1].map((fraction) =>
      this.comparison === "population_normalized"
        ? this.metricMax * fraction
        : Math.max(1, Math.round(this.metricMax * fraction)),
    );
    const items = document.createElement("div");
    items.className = "bubble-legend-items";
    values.forEach((value) => {
      const item = document.createElement("span");
      item.className = "bubble-legend-item";
      const bubble = document.createElement("i");
      const diameter = markerRadius(value, this.metricMax) * 2;
      bubble.style.width = `${diameter}px`;
      bubble.style.height = `${diameter}px`;
      const label = document.createElement("span");
      label.textContent = this.comparison === "population_normalized"
        ? decimalFormat.format(value)
        : compactFormat.format(value);
      item.append(bubble, label);
      items.append(item);
    });
    this.legendScale.append(title, items);
    this.legend.setAttribute(
      "aria-label",
      `Shared bubble size scale for ${this.comparison === "population_normalized" ? `population-normalized ${metricLabel}` : `total ${metricLabel}`}, from ${this.comparison === "population_normalized" ? decimalFormat.format(values[0]) : integerFormat.format(values[0])} to ${this.comparison === "population_normalized" ? decimalFormat.format(values[2]) : integerFormat.format(values[2])}.`,
    );
  }

  updateMarkerLabel(placeId) {
    const marker = this.markers.get(placeId);
    if (!marker) return;
    const { place, group } = marker;
    const metric = this.metricDetails(place);
    const leaderId =
      this.metric === "followers"
        ? place.leadingBandFollowersId
        : place.leadingBandMonthlyListenersId;
    const leader = this.bandById.get(leaderId);
    const scope = this.comparison === "population_normalized"
      ? `OECD Functional Urban Area with 2024 population ${integerFormat.format(place.population)}`
      : place.placeType;
    const bandScope = this.comparison === "population_normalized"
      ? "mapped catalog"
      : "catalog";
    group.setAttribute(
      "aria-label",
      `${place.label}, ${scope}. ${metric.formattedValue} ${metric.accessibleLabel} across ${place.bandCount} ${bandScope} ${place.bandCount === 1 ? "band" : "bands"}. Leading band: ${leader?.name || "unavailable"}.`,
    );
  }

  showTooltip(place) {
    const marker = this.markers.get(place.id);
    const metric = this.metricDetails(place);
    const leaderId =
      this.metric === "followers"
        ? place.leadingBandFollowersId
        : place.leadingBandMonthlyListenersId;
    const leader = this.bandById.get(leaderId);
    const population = this.comparison === "population_normalized"
      ? ` · ${integerFormat.format(place.population)} residents (${place.populationYear})`
      : "";
    const bandScope = this.comparison === "population_normalized" ? "mapped " : "";
    this.tooltip.textContent = `${place.label} · ${metric.formattedValue} ${metric.label}${population} · ${place.bandCount} ${bandScope}${place.bandCount === 1 ? "band" : "bands"} · leads: ${leader?.name || "Unavailable"}`;
    this.tooltip.style.left = `${((marker.x * this.zoom + this.translateX) / WIDTH) * 100}%`;
    this.tooltip.style.top = `${((marker.y * this.zoom + this.translateY) / HEIGHT) * 100}%`;
    this.tooltip.hidden = false;
  }

  hideTooltip() {
    this.tooltip.hidden = true;
  }

  applyTransform() {
    this.viewport.setAttribute(
      "transform",
      `translate(${this.translateX},${this.translateY}) scale(${this.zoom})`,
    );
    this.markers.forEach(({ hit, dot, ring, group, place }) => {
      const radius = markerRadius(
        placeMetricValue(place, this.metric, this.comparison),
        this.metricMax,
      );
      hit.setAttribute("r", String(Math.max(11, radius + 2) / this.zoom));
      dot.setAttribute("r", String(radius / this.zoom));
      ring.setAttribute("r", String(Math.max(6.2, radius + 3) / this.zoom));
      group.style.setProperty("--map-inverse-zoom", String(1 / this.zoom));
    });
    this.labels.forEach(({ text, offset }) => {
      text.setAttribute("x", String(offset.x / this.zoom));
      text.setAttribute("y", String(offset.y / this.zoom));
      text.style.fontSize = `${MAP_LABEL_FONT_SIZE / this.zoom}px`;
    });
  }
}
