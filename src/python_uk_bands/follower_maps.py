"""Geographic follower maps for the frozen top-1,000 band experiment."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd

from .visuals import HOUSE, add_superposed_bubble_legend, apply_chart_style


FOLLOWERS_PER_POINT_SQUARED = 100_000
QUOTIENT_POINTS_SQUARED_PER_UNIT = 850
UK_MAP_EXTENT = (-10.5, 5.2, 49.5, 61.1)
DEFAULT_LABEL_POSITIONS: dict[str, tuple[float, float]] = {
    "Glasgow": (-7.7, 56.35),
    "Liverpool": (-7.7, 54.45),
    "Manchester": (-7.7, 53.62),
    "Birmingham": (-7.7, 52.72),
    "Oxford": (-7.7, 51.82),
    "Exeter": (-7.7, 50.45),
    "Leeds": (2.55, 54.72),
    "Sheffield": (2.55, 53.87),
    "London": (2.55, 52.20),
    "Crawley": (2.55, 51.30),
}


def prepare_top_city_map_data(
    shares: pd.DataFrame,
    coordinates: pd.DataFrame,
    photo_manifest: pd.DataFrame,
    *,
    top_city_count: int = 10,
) -> pd.DataFrame:
    """Join the leading follower cities to frozen coordinates and photos."""

    required_shares = {
        "fua_code",
        "study_city_label",
        "band_count",
        "followers_total",
        "follower_share",
        "follower_output_quotient",
        "largest_band_by_followers",
        "largest_band_followers",
        "largest_band_follower_share",
    }
    required_coordinates = {
        "fua_code",
        "study_city_label",
        "latitude",
        "longitude",
        "coordinate_source_url",
    }
    required_manifest = {
        "fua_code",
        "study_city_label",
        "band_name",
        "commons_page_url",
        "local_path",
        "artist",
        "license_short_name",
        "license_url",
        "attribution_text",
    }
    for frame, required, label in [
        (shares, required_shares, "shares"),
        (coordinates, required_coordinates, "coordinates"),
        (photo_manifest, required_manifest, "photo manifest"),
    ]:
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} is missing columns: {sorted(missing)}")
    if top_city_count <= 0:
        raise ValueError("top_city_count must be positive")
    if shares["fua_code"].duplicated().any():
        raise ValueError("shares must contain one row per FUA")
    if coordinates["fua_code"].duplicated().any():
        raise ValueError("coordinates must contain one row per FUA")
    if photo_manifest["fua_code"].duplicated().any():
        raise ValueError("photo manifest must contain one row per FUA")

    positive = shares.loc[shares["followers_total"].gt(0)].copy()
    if len(positive) < top_city_count:
        raise ValueError(
            f"Only {len(positive)} positive-output FUAs are available for "
            f"top_city_count={top_city_count}"
        )
    top = (
        positive.sort_values(
            ["followers_total", "study_city_label"],
            ascending=[False, True],
        )
        .head(top_city_count)
        .reset_index(drop=True)
    )
    top.insert(0, "rank_by_followers", np.arange(1, len(top) + 1))
    coordinate_columns = [
        "fua_code",
        "study_city_label",
        "latitude",
        "longitude",
        "city_qid",
        "coordinate_source_url",
    ]
    coordinate_columns = [
        column for column in coordinate_columns if column in coordinates.columns
    ]
    manifest_columns = [
        "fua_code",
        "study_city_label",
        "band_name",
        "band_qid",
        "commons_filename",
        "commons_page_url",
        "local_path",
        "image_sha256",
        "artist",
        "credit",
        "license_short_name",
        "license_url",
        "attribution_text",
    ]
    manifest_columns = [
        column for column in manifest_columns if column in photo_manifest.columns
    ]
    top = top.merge(
        coordinates[coordinate_columns],
        on=["fua_code", "study_city_label"],
        how="left",
        validate="one_to_one",
    ).merge(
        photo_manifest[manifest_columns],
        on=["fua_code", "study_city_label"],
        how="left",
        validate="one_to_one",
    )
    if top[["latitude", "longitude", "local_path"]].isna().any().any():
        raise ValueError("Every selected city requires coordinates and a photo")
    mismatched_band = top["largest_band_by_followers"].ne(top["band_name"])
    if mismatched_band.any():
        rows = top.loc[
            mismatched_band,
            ["study_city_label", "largest_band_by_followers", "band_name"],
        ]
        raise ValueError(
            "Photo band must match the largest-followed band: "
            + rows.to_dict(orient="records").__repr__()
        )

    mapped_followers = float(shares["followers_total"].sum())
    top["share_of_mapped_followers"] = (
        top["followers_total"] / mapped_followers
    )
    top["circle_area_points2"] = (
        top["followers_total"] / FOLLOWERS_PER_POINT_SQUARED
    )
    top["quotient_circle_area_points2"] = (
        top["follower_output_quotient"] * QUOTIENT_POINTS_SQUARED_PER_UNIT
    )
    return top


def load_geojson(path: str | Path) -> dict[str, Any]:
    """Load a frozen GeoJSON feature collection."""

    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("type") != "FeatureCollection" or not payload.get(
        "features"
    ):
        raise ValueError("Expected a non-empty GeoJSON FeatureCollection")
    return payload


def _iter_exterior_rings(geometry: dict[str, Any]):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        polygons = [coordinates]
    elif geometry_type == "MultiPolygon":
        polygons = coordinates
    else:
        raise ValueError(f"Unsupported GeoJSON geometry: {geometry_type}")
    for polygon in polygons:
        if polygon:
            yield np.asarray(polygon[0], dtype=float)


def _draw_uk_outline(ax: plt.Axes, geography: dict[str, Any]) -> None:
    for feature in geography["features"]:
        for ring in _iter_exterior_rings(feature["geometry"]):
            ax.add_patch(
                Polygon(
                    ring,
                    closed=True,
                    facecolor=HOUSE["paper_soft"],
                    edgecolor=HOUSE["muted"],
                    linewidth=0.65,
                    zorder=1,
                )
            )


def _format_followers(value: float) -> str:
    if value >= 100_000_000:
        return f"{value / 1_000_000:.0f}m"
    if value >= 10_000_000:
        return f"{value / 1_000_000:.1f}m"
    return f"{value / 1_000_000:.2f}m"


def _setup_map(
    geography: dict[str, Any],
    *,
    title: str,
    subtitle: str,
) -> tuple[plt.Figure, plt.Axes]:
    apply_chart_style()
    figure, ax = plt.subplots(figsize=(10.6, 10.4))
    _draw_uk_outline(ax, geography)
    west, east, south, north = UK_MAP_EXTENT
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect(1 / math.cos(math.radians((south + north) / 2)))
    ax.axis("off")
    figure.suptitle(
        title,
        x=0.08,
        y=0.965,
        ha="left",
        fontsize=17,
        fontweight="normal",
        color=HOUSE["ink"],
    )
    figure.text(
        0.08,
        0.926,
        subtitle,
        ha="left",
        va="top",
        fontsize=10,
        color=HOUSE["secondary"],
    )
    figure.subplots_adjust(left=0.08, right=0.96, bottom=0.09, top=0.895)
    return figure, ax


def _annotate_cities(
    ax: plt.Axes,
    data: pd.DataFrame,
    *,
    include_band: bool,
) -> None:
    for row in data.itertuples(index=False):
        position = DEFAULT_LABEL_POSITIONS.get(
            row.study_city_label,
            (row.longitude + 0.5, row.latitude + 0.2),
        )
        if include_band:
            label = (
                f"{row.study_city_label}\n"
                f"{row.band_name} · {_format_followers(row.followers_total)}"
            )
        else:
            label = (
                f"{row.study_city_label}\n"
                f"{_format_followers(row.followers_total)}"
            )
        ax.annotate(
            label,
            xy=(row.longitude, row.latitude),
            xytext=position,
            textcoords="data",
            ha="left" if position[0] > row.longitude else "right",
            va="center",
            fontsize=8.6,
            color=HOUSE["ink_soft"],
            linespacing=1.15,
            arrowprops={
                "arrowstyle": "-",
                "color": HOUSE["secondary"],
                "linewidth": 0.65,
                "shrinkA": 3,
                "shrinkB": 4,
                "connectionstyle": "arc3,rad=0",
            },
            zorder=20,
        )


def _annotate_output_quotients(ax: plt.Axes, data: pd.DataFrame) -> None:
    for row in data.itertuples(index=False):
        position = DEFAULT_LABEL_POSITIONS.get(
            row.study_city_label,
            (row.longitude + 0.5, row.latitude + 0.2),
        )
        label = (
            f"{row.study_city_label}\n"
            f"{row.follower_output_quotient:.2f}×"
        )
        ax.annotate(
            label,
            xy=(row.longitude, row.latitude),
            xytext=position,
            textcoords="data",
            ha="left" if position[0] > row.longitude else "right",
            va="center",
            fontsize=8.6,
            color=HOUSE["ink_soft"],
            linespacing=1.15,
            arrowprops={
                "arrowstyle": "-",
                "color": HOUSE["secondary"],
                "linewidth": 0.65,
                "shrinkA": 3,
                "shrinkB": 4,
                "connectionstyle": "arc3,rad=0",
            },
            zorder=20,
        )


def _save_map(
    figure: plt.Figure,
    output_path: str | Path,
    *,
    note: str,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.text(
        0.08,
        0.035,
        note,
        ha="left",
        va="bottom",
        fontsize=8.3,
        color=HOUSE["secondary"],
        linespacing=1.35,
    )
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=HOUSE["page"],
    )
    plt.show()
    return output_path


def plot_city_follower_bubbles(
    data: pd.DataFrame,
    geography: dict[str, Any],
    *,
    snapshot_date: str,
    output_path: str | Path,
) -> Path:
    """Map top FUAs with follower-proportional circle areas."""

    figure, ax = _setup_map(
        geography,
        title="Largest combined band followings by UK city",
        subtitle=(
            f"Top {len(data)} UK FUAs · bubble area is proportional to combined "
            f"Spotify followers · frozen {snapshot_date} snapshot"
        ),
    )
    draw_order = data.sort_values("followers_total", ascending=False)
    ax.scatter(
        draw_order["longitude"],
        draw_order["latitude"],
        s=draw_order["circle_area_points2"],
        facecolor=HOUSE["blue_soft"],
        edgecolor=HOUSE["blue"],
        linewidth=1.1,
        alpha=0.88,
        zorder=5,
    )
    follower_references = (10_000_000.0, 50_000_000.0, 100_000_000.0)
    add_superposed_bubble_legend(
        ax,
        title="Bubble area · combined Spotify followers",
        areas=tuple(
            value / FOLLOWERS_PER_POINT_SQUARED
            for value in follower_references
        ),
        labels=tuple(_format_followers(value) for value in follower_references),
        loc="upper right",
    )
    _annotate_cities(ax, data, include_band=False)
    return _save_map(
        figure,
        output_path,
        note=(
            "Bubble area is proportional to combined followers across mapped bands in each FUA. "
            "Pins use city-centre coordinates to represent the whole FUA; overlapping circles remain geographically fixed."
        ),
    )


def _circular_image(path: str | Path) -> np.ndarray:
    image = mpimg.imread(path)
    if image.ndim == 2:
        image = np.repeat(image[:, :, np.newaxis], 3, axis=2)
    height, width = image.shape[:2]
    size = min(height, width)
    top = (height - size) // 2
    left = (width - size) // 2
    square = image[top : top + size, left : left + size]
    if square.shape[2] == 3:
        alpha_base = np.ones(square.shape[:2], dtype=float)
        rgb = square
    elif square.shape[2] == 4:
        rgb = square[:, :, :3]
        alpha_base = square[:, :, 3].astype(float)
        if np.issubdtype(square.dtype, np.integer):
            alpha_base /= np.iinfo(square.dtype).max
    else:
        raise ValueError(f"Unsupported image shape for {path}: {square.shape}")
    yy, xx = np.ogrid[:size, :size]
    centre = (size - 1) / 2
    radius = size / 2 - 1
    distance = np.sqrt((xx - centre) ** 2 + (yy - centre) ** 2)
    mask = np.clip(radius - distance + 0.75, 0, 1)
    alpha = alpha_base * mask
    if np.issubdtype(rgb.dtype, np.integer):
        alpha = np.rint(alpha * np.iinfo(rgb.dtype).max).astype(rgb.dtype)
    else:
        alpha = alpha.astype(rgb.dtype)
    return np.dstack([rgb, alpha])


def plot_city_follower_photo_bubbles(
    data: pd.DataFrame,
    geography: dict[str, Any],
    *,
    project_root: str | Path,
    snapshot_date: str,
    output_path: str | Path,
) -> Path:
    """Map follower-proportional circles filled with each FUA's top band."""

    project_root = Path(project_root)
    figure, ax = _setup_map(
        geography,
        title="The leading band inside each city's following",
        subtitle=(
            f"Same top {len(data)} FUAs and bubble-area scale · each photo is the "
            "city's largest-followed selected band"
        ),
    )
    for row in data.sort_values("followers_total", ascending=False).itertuples(
        index=False
    ):
        image = _circular_image(project_root / row.local_path)
        diameter_points = 2 * math.sqrt(row.circle_area_points2 / math.pi)
        offset_image = OffsetImage(
            image,
            zoom=diameter_points / image.shape[1],
            interpolation="lanczos",
        )
        annotation = AnnotationBbox(
            offset_image,
            (row.longitude, row.latitude),
            frameon=False,
            pad=0,
            box_alignment=(0.5, 0.5),
            zorder=7,
        )
        ax.add_artist(annotation)
        ax.scatter(
            [row.longitude],
            [row.latitude],
            s=[row.circle_area_points2],
            facecolor="none",
            edgecolor=HOUSE["ink"],
            linewidth=0.9,
            zorder=8,
        )
    follower_references = (10_000_000.0, 50_000_000.0, 100_000_000.0)
    add_superposed_bubble_legend(
        ax,
        title="Bubble area · combined Spotify followers",
        areas=tuple(
            value / FOLLOWERS_PER_POINT_SQUARED
            for value in follower_references
        ),
        labels=tuple(_format_followers(value) for value in follower_references),
        loc="upper right",
    )
    _annotate_cities(ax, data, include_band=True)
    return _save_map(
        figure,
        output_path,
        note=(
            f"Bubble area remains proportional to city follower total (snapshot {snapshot_date}). "
            "The image identifies only the largest-followed mapped band, not every band in the FUA. "
            "Photo credits and licences appear below."
        ),
    )


def plot_city_follower_output_quotient(
    data: pd.DataFrame,
    geography: dict[str, Any],
    *,
    snapshot_date: str,
    output_path: str | Path,
) -> Path:
    """Map follower share relative to FUA population share."""

    required = {
        "study_city_label",
        "latitude",
        "longitude",
        "follower_output_quotient",
        "quotient_circle_area_points2",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(
            f"Output-quotient map data is missing columns: {sorted(missing)}"
        )
    if (data["follower_output_quotient"] < 0).any():
        raise ValueError("Follower output quotients must be non-negative")

    figure, ax = _setup_map(
        geography,
        title="Follower output quotient by UK city",
        subtitle=(
            f"Same top {len(data)} FUAs · follower share ÷ population share · "
            f"1× is proportional output · frozen {snapshot_date} snapshot"
        ),
    )
    draw_order = data.sort_values(
        "follower_output_quotient", ascending=False
    )
    above = draw_order.loc[draw_order["follower_output_quotient"].ge(1)]
    below = draw_order.loc[draw_order["follower_output_quotient"].lt(1)]
    if not above.empty:
        ax.scatter(
            above["longitude"],
            above["latitude"],
            s=above["quotient_circle_area_points2"],
            facecolor=HOUSE["blue_soft"],
            edgecolor=HOUSE["blue"],
            linewidth=1.1,
            alpha=0.92,
            zorder=5,
        )
    if not below.empty:
        ax.scatter(
            below["longitude"],
            below["latitude"],
            s=below["quotient_circle_area_points2"],
            facecolor=HOUSE["page"],
            edgecolor=HOUSE["secondary"],
            linewidth=1.1,
            zorder=6,
        )

    quotient_references = (0.5, 1.0, 3.0)
    add_superposed_bubble_legend(
        ax,
        title="Bubble area · follower output quotient",
        areas=tuple(
            value * QUOTIENT_POINTS_SQUARED_PER_UNIT
            for value in quotient_references
        ),
        labels=tuple(f"{value:g}×" for value in quotient_references),
        items=[
            {
                "kind": "marker",
                "label": "At or above 1×",
                "facecolor": HOUSE["blue_soft"],
                "edgecolor": HOUSE["blue"],
            },
            {
                "kind": "marker",
                "label": "Below 1×",
                "facecolor": HOUSE["page"],
                "edgecolor": HOUSE["secondary"],
            },
        ],
        loc="upper right",
    )
    _annotate_output_quotients(ax, data)
    return _save_map(
        figure,
        output_path,
        note=(
            "Bubble area is proportional to the follower output quotient, not raw followers. "
            "Filled circles are at or above 1×; open circles are below 1×. "
            "Cities remain the top ten selected by combined followers."
        ),
    )
