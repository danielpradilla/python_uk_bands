export function normalizeSearch(value) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("en-GB")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function matchScore(values, normalized, terms) {
  const candidates = values.map(normalizeSearch).filter(Boolean);
  if (candidates.some((candidate) => candidate === normalized)) return 0;
  if (candidates.some((candidate) => candidate.startsWith(normalized))) return 1;
  if (
    candidates.some((candidate) => {
      const words = candidate.split(" ");
      return terms.every((term) => words.some((word) => word.startsWith(term)));
    })
  ) {
    return 2;
  }
  return terms.every((term) => candidates.some((candidate) => candidate.includes(term)))
    ? 3
    : null;
}

export function searchExplorer(bands, places, query, limit = 10) {
  const normalized = normalizeSearch(query);
  if (!normalized) return [];
  const terms = normalized.split(" ");
  const results = [];

  bands.forEach((band) => {
    const score = matchScore([band.name, band.catalogName], normalized, terms);
    if (score !== null) {
      results.push({ type: "band", band, score });
    }
  });

  places.forEach((place) => {
    const score = matchScore([place.label], normalized, terms);
    if (score !== null) {
      results.push({ type: "place", place, score });
    }
  });

  return results
    .sort((a, b) => {
      if (a.score !== b.score) return a.score - b.score;
      if (a.type !== b.type) return a.type === "place" ? -1 : 1;
      if (a.type === "band") {
        return a.band.catalogRank - b.band.catalogRank || a.band.name.localeCompare(b.band.name);
      }
      return a.place.label.localeCompare(b.place.label);
    })
    .slice(0, limit)
    .map(({ score, ...result }) => result);
}
