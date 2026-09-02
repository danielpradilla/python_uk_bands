#!/usr/bin/env python3
"""Fact-check the top-1,000 catalogue's formation places.

The audit compares the frozen Wikidata-derived claim with MusicBrainz begin
areas and English Wikipedia musical-artist infobox origins. It does not silently
rewrite the catalogue: disagreements and unsupported rows remain review cases.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import time
import unicodedata

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/processed/popularity_first_top1000_20260718T204522Z_bands.csv"
WIKIDATA = ROOT / "data/raw/wikidata/review_extension_entities_20260725.json"
DASHBOARD = ROOT / "interactive/public/data/dashboard.json"
MB_RAW = ROOT / "data/raw/musicbrainz/top1000_origin_areas_20260901.json"
WIKI_RAW = ROOT / "data/raw/wikipedia/top1000_origin_infobox_20260901.json"
AUDIT = ROOT / "data/processed/top1000_origin_fact_check_20260901.csv"
REPORT = ROOT / "data/processed/top1000_origin_fact_check_20260901_report.json"
DECISIONS = ROOT / "reference/top1000_origin_fact_check_decisions_20260902.csv"

USER_AGENT = (
    "uk-music-cities-origin-audit/1.0 "
    "(https://github.com/danielpradilla/uk-music-cities)"
)
GENERIC_PLACES = {
    "",
    "england",
    "great britain",
    "northern ireland",
    "scotland",
    "united kingdom",
    "uk",
    "wales",
}
PLACE_ALIASES = {
    "abingdononthames": "abingdon",
    "kingstonuponhull": "hull",
    "isleofskye": "skye",
    "newcastleupontyne": "newcastle",
    "newyorkcity": "newyork",
    "redcliffecity": "redcliffe",
    "stokeontrent": "stoke",
}
INFOBOX_ORIGIN = re.compile(
    r"(?ims)^\s*\|\s*origin\s*=\s*(.*?)"
    r"(?=^\s*\|\s*[a-z][a-z0-9 _-]*\s*=|^\s*\}\})"
)


def _write_json(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _get_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, object],
) -> dict:
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            response = session.get(url, params=params, timeout=90)
        except requests.RequestException as error:
            last_error = error
            time.sleep(min(30, 2 ** attempt))
            continue
        if response.status_code == 200:
            return response.json()
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
        last_error = requests.HTTPError(
            f"{response.status_code} from {response.url}", response=response
        )
        time.sleep(min(30, 2 ** attempt))
    if last_error:
        raise last_error
    response.raise_for_status()
    raise RuntimeError("unreachable")


def _wikidata_musicbrainz_ids() -> dict[str, list[str]]:
    payload = json.loads(WIKIDATA.read_text())
    result: dict[str, list[str]] = {}
    for qid, entity in payload["entities"].items():
        values = []
        for claim in entity.get("claims", {}).get("P434", []):
            value = (
                claim.get("mainsnak", {})
                .get("datavalue", {})
                .get("value")
            )
            if isinstance(value, str):
                values.append(value)
        result[qid] = sorted(set(values))
    return result


def capture_musicbrainz(*, force: bool) -> dict:
    qid_to_ids = _wikidata_musicbrainz_ids()
    ids = sorted({value for values in qid_to_ids.values() for value in values})
    existing = json.loads(MB_RAW.read_text()) if MB_RAW.exists() else {}
    if existing.get("complete") and not force:
        return existing
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    artists: dict[str, dict] = {} if force else existing.get("artists", {})
    errors: dict[str, str] = {} if force else existing.get("errors", {})
    remaining = [value for value in ids if value not in artists]
    def add_artist(artist: dict) -> None:
        artists[artist["id"]] = {
            "id": artist["id"],
            "name": artist.get("name", ""),
            "type": artist.get("type", ""),
            "country": artist.get("country", ""),
            "area": artist.get("area", {}),
            "begin_area": artist.get("begin-area", {}),
            "life_span": artist.get("life-span", {}),
            "score": artist.get("score"),
        }
    batch_size = 15
    for start in range(0, len(remaining), batch_size):
        batch = remaining[start : start + batch_size]
        query = " OR ".join(f"arid:{value}" for value in batch)
        try:
            response = _get_json(
                session,
                "https://musicbrainz.org/ws/2/artist",
                params={"query": query, "fmt": "json", "limit": 100},
            )
            for artist in response.get("artists", []):
                add_artist(artist)
        except requests.RequestException:
            print(f"MusicBrainz batch fallback: {batch[0]}…", flush=True)
            for mbid in batch:
                try:
                    add_artist(
                        _get_json(
                            session,
                            f"https://musicbrainz.org/ws/2/artist/{mbid}",
                            params={"fmt": "json"},
                        )
                    )
                    errors.pop(mbid, None)
                except requests.RequestException as error:
                    errors[mbid] = str(error)
                time.sleep(1.1)
        payload = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_url": "https://musicbrainz.org/ws/2/artist",
            "input_path": str(WIKIDATA.relative_to(ROOT)),
            "requested_ids": len(ids),
            "returned_ids": len(artists),
            "errors": errors,
            "complete": False,
            "artists": artists,
        }
        _write_json(payload, MB_RAW)
        if start + batch_size < len(remaining):
            time.sleep(1.1)
        print(f"MusicBrainz {len(artists)}/{len(ids)}", flush=True)

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": "https://musicbrainz.org/ws/2/artist",
        "input_path": str(WIKIDATA.relative_to(ROOT)),
        "requested_ids": len(ids),
        "returned_ids": len(artists),
        "errors": errors,
        "complete": True,
        "artists": artists,
    }
    _write_json(payload, MB_RAW)
    return payload


def _extract_origin(wikitext: str) -> str:
    match = INFOBOX_ORIGIN.search(wikitext)
    return match.group(1).strip() if match else ""


def _plain_wikitext(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>", "", value, flags=re.I | re.S)
    value = re.sub(r"<br\s*/?>", "; ", value, flags=re.I)
    value = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    for _ in range(4):
        updated = re.sub(
            r"\{\{(?:hlist|flatlist|plainlist|ubl|unbulleted list)\s*\|(.*?)\}\}",
            lambda match: "; ".join(
                part.strip(" *\n") for part in match.group(1).split("|") if part.strip(" *\n")
            ),
            value,
            flags=re.I | re.S,
        )
        updated = re.sub(r"\{\{[^{}|]+\|([^{}]+)\}\}", r"\1", updated)
        if updated == value:
            break
        value = updated
    value = re.sub(
        r"^\{\{(?:hlist|flatlist|plainlist|ubl|unbulleted list)\s*\|",
        "",
        value,
        flags=re.I,
    )
    value = re.sub(r"\{\{.*?\}\}", "", value, flags=re.S)
    value = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip(" *;,\n")


def capture_wikipedia(*, force: bool) -> dict:
    if WIKI_RAW.exists() and not force:
        return json.loads(WIKI_RAW.read_text())

    bands = json.loads(DASHBOARD.read_text())["bands"]
    titles = sorted({band["wikipediaTitle"] for band in bands if band["wikipediaTitle"]})
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    pages: dict[str, dict] = {}
    for start in range(0, len(titles), 40):
        batch = titles[start : start + 40]
        response = _get_json(
            session,
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "prop": "revisions",
                "titles": "|".join(batch),
                "rvprop": "timestamp|content",
                "rvslots": "main",
                "format": "json",
                "formatversion": 2,
            },
        )
        for page in response.get("query", {}).get("pages", []):
            revision = (page.get("revisions") or [{}])[0]
            wikitext = revision.get("slots", {}).get("main", {}).get("content", "")
            raw_origin = _extract_origin(wikitext)
            pages[page.get("title", "")] = {
                "requested_title": next(
                    (
                        title
                        for title in batch
                        if title == page.get("title")
                        or title in response.get("query", {}).get("normalized", [])
                    ),
                    page.get("title", ""),
                ),
                "pageid": page.get("pageid"),
                "title": page.get("title", ""),
                "revision_timestamp": revision.get("timestamp", ""),
                "origin_raw": raw_origin,
                "origin_plain": _plain_wikitext(raw_origin),
            }
        print(f"Wikipedia {min(start + 40, len(titles))}/{len(titles)}", flush=True)

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": "https://en.wikipedia.org/w/api.php",
        "input_path": str(DASHBOARD.relative_to(ROOT)),
        "requested_titles": len(titles),
        "returned_pages": len(pages),
        "pages": pages,
    }
    _write_json(payload, WIKI_RAW)
    return payload


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"\b(?:england|great britain|northern ireland|scotland|united kingdom|uk|wales)\b", "", value)
    value = re.sub(r"[^a-z0-9]+", "", value)
    return PLACE_ALIASES.get(value, value)


def _usable_place(value: str) -> bool:
    normalized = _normalize(value)
    return bool(normalized) and value.strip().casefold() not in GENERIC_PLACES


def _place_segments(value: str) -> list[str]:
    parts = re.split(r"\s*(?:,|;|/|\||\band\b)\s*", value, flags=re.I)
    return [part.strip() for part in parts if _usable_place(part)]


def _places_match(claim: str, evidence: str) -> bool | None:
    if not _usable_place(evidence):
        return None
    if not _usable_place(claim):
        return False
    claim_normalized = _normalize(claim)
    evidence_values = {_normalize(evidence), *(_normalize(part) for part in _place_segments(evidence))}
    return any(
        candidate == claim_normalized
        or (
            len(candidate) >= 5
            and len(claim_normalized) >= 5
            and (candidate in claim_normalized or claim_normalized in candidate)
        )
        for candidate in evidence_values
        if candidate
    )


def _current_claim(row: pd.Series) -> str:
    if row["origin_override"]:
        return row["origin_override"]
    if row["origin_resolution"] == "reviewed_multi_place_rule":
        return row["origin_cluster"]
    formation = row["formation_label"]
    if "|" in formation or re.fullmatch(r"Q\d+", formation) or not _usable_place(formation):
        return ""
    return formation


def _first_specific_place(value: str) -> str:
    return next(iter(_place_segments(value)), "")


def build_audit(musicbrainz: dict, wikipedia: dict) -> pd.DataFrame:
    catalog = pd.read_csv(CATALOG, keep_default_na=False)
    dashboard = {
        band["id"]: band for band in json.loads(DASHBOARD.read_text())["bands"]
    }
    qid_to_ids = _wikidata_musicbrainz_ids()
    mb_artists = musicbrainz["artists"]
    wiki_pages = wikipedia["pages"]
    wiki_by_title = {page["title"]: page for page in wiki_pages.values()}

    rows = []
    for _, band in catalog.iterrows():
        spotify_id = band["returned_spotify_id"]
        mbids = qid_to_ids.get(band["wikidata_qid"], [])
        mb_records = [mb_artists[value] for value in mbids if value in mb_artists]
        mb_begin_areas = sorted(
            {
                (record.get("begin_area") or {}).get("name", "")
                for record in mb_records
                if (record.get("begin_area") or {}).get("name", "")
            }
        )
        mb_area = "|".join(mb_begin_areas)
        dashboard_band = dashboard[spotify_id]
        wiki_title = dashboard_band.get("wikipediaTitle") or ""
        wiki = wiki_by_title.get(wiki_title, {})
        wiki_origin = _plain_wikitext(wiki.get("origin_raw", ""))
        claim = _current_claim(band)
        mb_match = _places_match(claim, mb_area)
        wiki_match = _places_match(claim, wiki_origin)
        available_matches = [value for value in [mb_match, wiki_match] if value is not None]

        proposed_origin = ""
        if claim:
            if available_matches.count(True) == 2:
                status = "corroborated_two_sources"
            elif True in available_matches and False in available_matches:
                status = "corroborated_with_source_variation"
            elif True in available_matches:
                status = "corroborated_one_source"
            elif False in available_matches:
                status = "conflict"
            else:
                status = "unverified"
        else:
            mb_proposal = _first_specific_place(mb_area)
            wiki_proposal = _first_specific_place(wiki_origin)
            if mb_proposal and wiki_proposal:
                if _places_match(mb_proposal, wiki_origin):
                    status = "proposed_two_sources"
                    proposed_origin = mb_proposal
                else:
                    status = "sources_conflict"
            elif mb_proposal or wiki_proposal:
                status = "proposed_one_source"
                proposed_origin = mb_proposal or wiki_proposal
            else:
                status = "unresolved"

        priority = ""
        if status in {
            "conflict",
            "sources_conflict",
            "corroborated_with_source_variation",
        }:
            priority = "high" if band["popularity_rank"] <= 200 else "medium"
        elif status.startswith("proposed"):
            priority = "high" if band["popularity_rank"] <= 200 else "medium"
        elif status in {"unverified", "unresolved"}:
            priority = "medium" if band["popularity_rank"] <= 200 else "low"

        rows.append(
            {
                "popularity_rank": band["popularity_rank"],
                "spotify_name": band["spotify_name"],
                "returned_spotify_id": spotify_id,
                "wikidata_qid": band["wikidata_qid"],
                "monthly_listeners": band["monthly_listeners"],
                "formation_label": band["formation_label"],
                "current_claim_place": claim,
                "current_origin_cluster": band["origin_cluster"],
                "current_origin_resolution": band["origin_resolution"],
                "wikidata_url": f"https://www.wikidata.org/wiki/{band['wikidata_qid']}",
                "musicbrainz_ids": "|".join(mbids),
                "musicbrainz_names": "|".join(sorted({record.get('name', '') for record in mb_records if record.get('name', '')})),
                "musicbrainz_begin_area": mb_area,
                "musicbrainz_urls": "|".join(f"https://musicbrainz.org/artist/{value}" for value in mbids),
                "musicbrainz_matches_claim": mb_match,
                "wikipedia_title": wiki_title,
                "wikipedia_origin": wiki_origin,
                "wikipedia_url": "https://en.wikipedia.org/wiki/" + requests.utils.quote(wiki_title.replace(" ", "_"), safe="_()") if wiki_title else "",
                "wikipedia_matches_claim": wiki_match,
                "automated_status": status,
                "proposed_origin": proposed_origin,
                "review_priority": priority,
                "manual_status": "pending" if priority else "not_required",
                "manual_decision": "",
                "manual_source_url": "",
                "manual_notes": "",
            }
        )
    audit = pd.DataFrame(rows)
    if DECISIONS.exists():
        decisions = pd.read_csv(DECISIONS, keep_default_na=False)
        audit = audit.drop(columns=["manual_status", "manual_decision", "manual_source_url", "manual_notes"]).merge(
            decisions,
            on="spotify_name",
            how="left",
            validate="one_to_one",
        )
        audit[["manual_status", "manual_decision", "manual_source_url", "manual_notes"]] = audit[
            ["manual_status", "manual_decision", "manual_source_url", "manual_notes"]
        ].fillna("")
    audit["final_status"] = audit["automated_status"].map(
        {
            "corroborated_two_sources": "confirmed",
            "corroborated_one_source": "confirmed",
            "proposed_two_sources": "evidence_for_missing_claim",
            "proposed_one_source": "evidence_for_missing_claim",
            "corroborated_with_source_variation": "source_variation",
            "conflict": "needs_review",
            "sources_conflict": "needs_review",
            "unverified": "unresolved",
            "unresolved": "unresolved",
        }
    )
    audit["final_origin"] = audit["current_claim_place"].where(
        audit["current_claim_place"].ne(""), audit["proposed_origin"]
    )
    decided = audit["manual_status"].isin({"confirmed", "corrected", "resolved", "contested"})
    audit.loc[decided, "final_status"] = audit.loc[decided, "manual_status"]
    audit.loc[decided, "final_origin"] = audit.loc[decided, "manual_decision"]
    audit.loc[~decided & audit["manual_status"].eq(""), "manual_status"] = "not_reviewed"
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    musicbrainz = capture_musicbrainz(force=args.force)
    wikipedia = capture_wikipedia(force=args.force)
    audit = build_audit(musicbrainz, wikipedia)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(AUDIT, index=False)
    counts = audit["automated_status"].value_counts().to_dict()
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(CATALOG.relative_to(ROOT)),
        "output": str(AUDIT.relative_to(ROOT)),
        "rows": len(audit),
        "status_counts": counts,
        "current_claim_rows": int(audit["current_claim_place"].ne("").sum()),
        "musicbrainz_begin_area_rows": int(audit["musicbrainz_begin_area"].ne("").sum()),
        "wikipedia_origin_rows": int(audit["wikipedia_origin"].ne("").sum()),
        "manual_review_rows": int(audit["review_priority"].ne("").sum()),
        "manual_decision_rows": int(audit["manual_status"].isin({"confirmed", "corrected", "resolved", "contested"}).sum()),
        "final_status_counts": audit["final_status"].value_counts().to_dict(),
        "method": (
            "Automated triangulation of the frozen Wikidata-derived claim "
            "against MusicBrainz begin-area and English Wikipedia infobox "
            "origin. Conflict and unsupported rows require manual review."
        ),
    }
    _write_json(report, REPORT)
    print(AUDIT.relative_to(ROOT))
    print(REPORT.relative_to(ROOT))
    print(json.dumps(report["status_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
