"""Population-scaling models for the top-N UK band experiments.

The project environment deliberately stays lightweight, so this module uses
NumPy implementations of an NB2 log-link model and HC3 log-log regression.
The negative-binomial fit profiles the dispersion parameter and re-fits the
regression coefficients at each candidate value.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from .visuals import HOUSE, add_superposed_bubble_legend, apply_chart_style


REQUIRED_COLUMNS = {
    "fua_code",
    "study_city_label",
    "population_year",
    "population",
    "population_share",
    "band_count",
    "followers_total",
    "follower_share",
    "largest_band_by_followers",
    "largest_band_follower_share",
}


def _validate_scaling_frame(shares: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(shares.columns)
    if missing:
        raise ValueError(f"Scaling frame is missing columns: {sorted(missing)}")
    if shares["fua_code"].duplicated().any():
        raise ValueError("Scaling frame must contain one row per FUA")

    frame = shares.copy()
    for column in [
        "population",
        "population_share",
        "band_count",
        "followers_total",
        "follower_share",
        "largest_band_follower_share",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if (frame["population"] <= 0).any():
        raise ValueError("FUA populations must be positive")
    if (frame[["band_count", "followers_total"]] < 0).any().any():
        raise ValueError("Music outputs must be non-negative")
    if not np.all(np.isfinite(frame["population"])):
        raise ValueError("FUA populations must be finite")
    return frame


def _two_sided_normal_p(z_score: float) -> float:
    return float(math.erfc(abs(z_score) / math.sqrt(2.0)))


def _log_factorials(values: np.ndarray) -> np.ndarray:
    return np.fromiter(
        (math.lgamma(float(value) + 1.0) for value in values),
        dtype=float,
        count=len(values),
    )


def _negative_binomial_log_likelihood(
    observed: np.ndarray,
    expected: np.ndarray,
    alpha: float,
) -> float:
    size = 1.0 / alpha
    log_gamma_y_plus_size = np.fromiter(
        (math.lgamma(float(value) + size) for value in observed),
        dtype=float,
        count=len(observed),
    )
    log_likelihood = (
        log_gamma_y_plus_size
        - math.lgamma(size)
        - _log_factorials(observed)
        + size * np.log(size / (size + expected))
        + observed * np.log(expected / (size + expected))
    )
    return float(log_likelihood.sum())


def _poisson_log_likelihood(
    observed: np.ndarray,
    expected: np.ndarray,
) -> float:
    return float(
        (
            observed * np.log(expected)
            - expected
            - _log_factorials(observed)
        ).sum()
    )


def _fit_log_link_coefficients(
    observed: np.ndarray,
    design: np.ndarray,
    *,
    alpha: float,
    start: np.ndarray | None = None,
    tolerance: float = 1e-11,
    max_iterations: int = 400,
) -> tuple[np.ndarray, np.ndarray, int, bool]:
    if start is None:
        coefficients = np.linalg.lstsq(
            design,
            np.log(observed + 0.5),
            rcond=None,
        )[0]
    else:
        coefficients = np.asarray(start, dtype=float).copy()

    converged = False
    information = np.eye(design.shape[1])
    for iteration in range(1, max_iterations + 1):
        linear_predictor = np.clip(design @ coefficients, -30.0, 30.0)
        expected = np.exp(linear_predictor)
        weights = expected / (1.0 + alpha * expected)
        working_response = linear_predictor + (observed - expected) / expected
        information = design.T @ (weights[:, None] * design)
        target = design.T @ (weights * working_response)
        updated = np.linalg.solve(information, target)
        if np.max(np.abs(updated - coefficients)) < tolerance:
            coefficients = updated
            converged = True
            break
        coefficients = updated

    linear_predictor = np.clip(design @ coefficients, -30.0, 30.0)
    expected = np.exp(linear_predictor)
    weights = expected / (1.0 + alpha * expected)
    information = design.T @ (weights[:, None] * design)
    covariance = np.linalg.inv(information)
    return coefficients, covariance, iteration, converged


def _profile_negative_binomial(
    observed: np.ndarray,
    design: np.ndarray,
) -> dict[str, object]:
    poisson_coefficients, _, _, _ = _fit_log_link_coefficients(
        observed,
        design,
        alpha=0.0,
    )

    cache: dict[float, tuple[float, np.ndarray, np.ndarray, int, bool]] = {}

    def evaluate(log_alpha: float) -> tuple[float, np.ndarray, np.ndarray, int, bool]:
        key = round(float(log_alpha), 12)
        if key not in cache:
            alpha = math.exp(log_alpha)
            coefficients, covariance, iterations, converged = (
                _fit_log_link_coefficients(
                    observed,
                    design,
                    alpha=alpha,
                    start=poisson_coefficients,
                )
            )
            expected = np.exp(np.clip(design @ coefficients, -30.0, 30.0))
            log_likelihood = _negative_binomial_log_likelihood(
                observed,
                expected,
                alpha,
            )
            cache[key] = (
                log_likelihood,
                coefficients,
                covariance,
                iterations,
                converged,
            )
        return cache[key]

    grid = np.linspace(-8.0, 4.0, 97)
    grid_scores = np.array([evaluate(value)[0] for value in grid])
    best_index = int(np.argmax(grid_scores))
    lower_index = max(0, best_index - 1)
    upper_index = min(len(grid) - 1, best_index + 1)
    lower = float(grid[lower_index])
    upper = float(grid[upper_index])

    golden_ratio = (math.sqrt(5.0) - 1.0) / 2.0
    left = upper - golden_ratio * (upper - lower)
    right = lower + golden_ratio * (upper - lower)
    left_score = evaluate(left)[0]
    right_score = evaluate(right)[0]
    for _ in range(100):
        if abs(upper - lower) < 1e-9:
            break
        if left_score > right_score:
            upper = right
            right = left
            right_score = left_score
            left = upper - golden_ratio * (upper - lower)
            left_score = evaluate(left)[0]
        else:
            lower = left
            left = right
            left_score = right_score
            right = lower + golden_ratio * (upper - lower)
            right_score = evaluate(right)[0]

    best_log_alpha = (lower + upper) / 2.0
    log_likelihood, coefficients, covariance, iterations, converged = evaluate(
        best_log_alpha
    )
    return {
        "alpha": math.exp(best_log_alpha),
        "coefficients": coefficients,
        "covariance": covariance,
        "log_likelihood": log_likelihood,
        "iterations": iterations,
        "converged": converged,
    }


def fit_negative_binomial_band_scaling(
    shares: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    """Fit an NB2 log-link model of mapped band count on FUA population."""

    frame = _validate_scaling_frame(shares)
    observed = frame["band_count"].to_numpy(dtype=float)
    log_population = np.log(frame["population"].to_numpy(dtype=float))
    log_population_center = float(log_population.mean())
    centered_log_population = log_population - log_population_center
    design = np.column_stack(
        [np.ones(len(frame), dtype=float), centered_log_population]
    )

    fit = _profile_negative_binomial(observed, design)
    coefficients = np.asarray(fit["coefficients"], dtype=float)
    covariance = np.asarray(fit["covariance"], dtype=float)
    alpha = float(fit["alpha"])
    expected = np.exp(np.clip(design @ coefficients, -30.0, 30.0))
    expected_variance = expected + alpha * expected**2
    pearson_residual = (observed - expected) / np.sqrt(expected_variance)
    linear_standard_error = np.sqrt(
        np.einsum("ij,jk,ik->i", design, covariance, design)
    )

    slope = float(coefficients[1])
    slope_standard_error = float(math.sqrt(covariance[1, 1]))
    slope_z_vs_one = (slope - 1.0) / slope_standard_error
    slope_ci_low = slope - 1.96 * slope_standard_error
    slope_ci_high = slope + 1.96 * slope_standard_error

    poisson_coefficients, _, poisson_iterations, poisson_converged = (
        _fit_log_link_coefficients(observed, design, alpha=0.0)
    )
    poisson_expected = np.exp(
        np.clip(design @ poisson_coefficients, -30.0, 30.0)
    )
    poisson_log_likelihood = _poisson_log_likelihood(
        observed,
        poisson_expected,
    )
    poisson_dispersion = float(
        (((observed - poisson_expected) ** 2 / poisson_expected).sum())
        / (len(frame) - design.shape[1])
    )

    intercept_design = np.ones((len(frame), 1), dtype=float)
    intercept_fit = _profile_negative_binomial(observed, intercept_design)
    null_log_likelihood = float(intercept_fit["log_likelihood"])
    model_log_likelihood = float(fit["log_likelihood"])

    results = frame.copy()
    results["expected_band_count"] = expected
    results["expected_count_mean_ci_low"] = np.exp(
        design @ coefficients - 1.96 * linear_standard_error
    )
    results["expected_count_mean_ci_high"] = np.exp(
        design @ coefficients + 1.96 * linear_standard_error
    )
    results["observed_to_expected_count"] = observed / expected
    results["count_difference"] = observed - expected
    results["pearson_residual"] = pearson_residual
    results["residual_rank"] = (
        results["pearson_residual"].rank(method="min", ascending=False).astype(int)
    )
    results = results.sort_values(
        ["pearson_residual", "study_city_label"],
        ascending=[False, True],
    ).reset_index(drop=True)

    summary: dict[str, float | int | str | bool] = {
        "model": "NB2 negative-binomial regression with log link",
        "outcome": "mapped top-1000 band count per FUA",
        "n_fuas": int(len(frame)),
        "positive_output_fuas": int((observed > 0).sum()),
        "zero_output_fuas": int((observed == 0).sum()),
        "observed_mapped_bands": int(observed.sum()),
        "population_year": int(frame["population_year"].iloc[0]),
        "log_population_center": log_population_center,
        "intercept_at_centered_log_population": float(coefficients[0]),
        "raw_log_population_intercept": float(
            coefficients[0] - slope * log_population_center
        ),
        "population_exponent_beta": slope,
        "beta_standard_error": slope_standard_error,
        "beta_ci_low": float(slope_ci_low),
        "beta_ci_high": float(slope_ci_high),
        "beta_test_value": 1.0,
        "beta_vs_one_z": float(slope_z_vs_one),
        "beta_equals_one_p_value": _two_sided_normal_p(slope_z_vs_one),
        "dispersion_alpha": alpha,
        "dispersion_theta": 1.0 / alpha,
        "log_likelihood": model_log_likelihood,
        "aic": float(-2.0 * model_log_likelihood + 2.0 * 3.0),
        "mcfadden_pseudo_r_squared": float(
            1.0 - model_log_likelihood / null_log_likelihood
        ),
        "poisson_aic": float(-2.0 * poisson_log_likelihood + 2.0 * 2.0),
        "poisson_pearson_dispersion": poisson_dispersion,
        "poisson_iterations": int(poisson_iterations),
        "poisson_converged": bool(poisson_converged),
        "iterations": int(fit["iterations"]),
        "converged": bool(fit["converged"]),
    }
    return results, summary


def _fit_ols_hc3(
    response: np.ndarray,
    design: np.ndarray,
) -> dict[str, np.ndarray | float]:
    inverse_information = np.linalg.inv(design.T @ design)
    coefficients = inverse_information @ design.T @ response
    fitted = design @ coefficients
    residuals = response - fitted
    leverage = np.einsum("ij,jk,ik->i", design, inverse_information, design)
    adjusted_squared_residuals = (residuals / (1.0 - leverage)) ** 2
    meat = design.T @ (adjusted_squared_residuals[:, None] * design)
    hc3_covariance = inverse_information @ meat @ inverse_information
    degrees_freedom = len(response) - design.shape[1]
    mean_squared_error = float((residuals @ residuals) / degrees_freedom)
    total_sum_squares = float(((response - response.mean()) ** 2).sum())
    r_squared = 1.0 - float(residuals @ residuals) / total_sum_squares
    studentized_residuals = residuals / np.sqrt(
        mean_squared_error * (1.0 - leverage)
    )
    cooks_distance = (
        residuals**2
        / (design.shape[1] * mean_squared_error)
        * leverage
        / (1.0 - leverage) ** 2
    )
    return {
        "coefficients": coefficients,
        "fitted": fitted,
        "residuals": residuals,
        "leverage": leverage,
        "hc3_covariance": hc3_covariance,
        "mse": mean_squared_error,
        "r_squared": r_squared,
        "studentized_residuals": studentized_residuals,
        "cooks_distance": cooks_distance,
    }


def _fit_huber_regression(
    response: np.ndarray,
    design: np.ndarray,
    *,
    tuning_constant: float = 1.345,
    tolerance: float = 1e-10,
    max_iterations: int = 300,
) -> np.ndarray:
    coefficients = np.linalg.lstsq(design, response, rcond=None)[0]
    for _ in range(max_iterations):
        residuals = response - design @ coefficients
        scale = 1.4826 * np.median(np.abs(residuals - np.median(residuals)))
        if scale <= 1e-12:
            break
        standardized = residuals / scale
        weights = np.ones_like(standardized)
        large = np.abs(standardized) > tuning_constant
        weights[large] = tuning_constant / np.abs(standardized[large])
        information = design.T @ (weights[:, None] * design)
        target = design.T @ (weights * response)
        updated = np.linalg.solve(information, target)
        if np.max(np.abs(updated - coefficients)) < tolerance:
            coefficients = updated
            break
        coefficients = updated
    return coefficients


def fit_loglog_follower_scaling(
    shares: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    """Fit HC3 log-log OLS to positive mapped follower totals."""

    frame = _validate_scaling_frame(shares)
    included_mask = frame["followers_total"].gt(0).to_numpy()
    included = frame.loc[included_mask].copy()
    if len(included) < 8:
        raise ValueError("Log-log regression requires at least eight positive FUAs")

    response = np.log(included["followers_total"].to_numpy(dtype=float))
    log_population = np.log(included["population"].to_numpy(dtype=float))
    log_population_center = float(log_population.mean())
    centered_log_population = log_population - log_population_center
    design = np.column_stack(
        [np.ones(len(included), dtype=float), centered_log_population]
    )
    fit = _fit_ols_hc3(response, design)
    coefficients = np.asarray(fit["coefficients"], dtype=float)
    covariance = np.asarray(fit["hc3_covariance"], dtype=float)
    fitted_log = np.asarray(fit["fitted"], dtype=float)
    residuals = np.asarray(fit["residuals"], dtype=float)
    leverage = np.asarray(fit["leverage"], dtype=float)
    linear_standard_error = np.sqrt(
        np.einsum("ij,jk,ik->i", design, covariance, design)
    )

    slope = float(coefficients[1])
    slope_standard_error = float(math.sqrt(covariance[1, 1]))
    slope_z_vs_one = (slope - 1.0) / slope_standard_error
    slope_ci_low = slope - 1.96 * slope_standard_error
    slope_ci_high = slope + 1.96 * slope_standard_error
    huber_coefficients = _fit_huber_regression(response, design)

    leave_one_out_slopes: list[float] = []
    for index in range(len(included)):
        keep = np.arange(len(included)) != index
        leave_one_out_slopes.append(
            float(np.linalg.lstsq(design[keep], response[keep], rcond=None)[0][1])
        )
    leave_one_out_slopes_array = np.array(leave_one_out_slopes)
    leave_one_out_errors = residuals / (1.0 - leverage)
    smearing_factor = float(np.mean(np.exp(residuals)))

    all_log_population = np.log(frame["population"].to_numpy(dtype=float))
    all_design = np.column_stack(
        [np.ones(len(frame)), all_log_population - log_population_center]
    )
    all_fitted_log = all_design @ coefficients
    all_linear_standard_error = np.sqrt(
        np.einsum("ij,jk,ik->i", all_design, covariance, all_design)
    )
    fitted_follower_median = np.exp(all_fitted_log)

    selected_follower_total = float(
        frame["followers_total"].sum() / frame["follower_share"].sum()
    )
    results = frame.copy()
    results["model_included"] = included_mask
    results["expected_follower_median"] = fitted_follower_median
    results["expected_follower_mean_smearing"] = (
        fitted_follower_median * smearing_factor
    )
    results["expected_follower_median_share"] = (
        fitted_follower_median / selected_follower_total
    )
    results["expected_median_ci_low"] = np.exp(
        all_fitted_log - 1.96 * all_linear_standard_error
    )
    results["expected_median_ci_high"] = np.exp(
        all_fitted_log + 1.96 * all_linear_standard_error
    )
    results["log_residual"] = np.nan
    results["studentized_log_residual"] = np.nan
    results["observed_to_expected_median"] = np.nan
    results["leverage"] = np.nan
    results["cooks_distance"] = np.nan
    results.loc[included_mask, "log_residual"] = residuals
    results.loc[included_mask, "studentized_log_residual"] = np.asarray(
        fit["studentized_residuals"], dtype=float
    )
    results.loc[included_mask, "observed_to_expected_median"] = np.exp(
        residuals
    )
    results.loc[included_mask, "leverage"] = leverage
    results.loc[included_mask, "cooks_distance"] = np.asarray(
        fit["cooks_distance"], dtype=float
    )
    results["residual_rank"] = (
        results["studentized_log_residual"]
        .rank(method="min", ascending=False, na_option="bottom")
        .astype(int)
    )
    results = results.sort_values(
        ["studentized_log_residual", "study_city_label"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)

    london_positions = np.flatnonzero(
        included["study_city_label"].eq("London").to_numpy()
    )
    beta_without_london = (
        float(leave_one_out_slopes_array[london_positions[0]])
        if len(london_positions)
        else float("nan")
    )
    most_influential_position = int(
        np.argmax(np.asarray(fit["cooks_distance"], dtype=float))
    )

    summary: dict[str, float | int | str | bool] = {
        "model": "OLS log-log regression with HC3 robust covariance",
        "outcome": "mapped follower total among positive-output FUAs",
        "n_fuas_total": int(len(frame)),
        "n_fuas_included": int(len(included)),
        "zero_output_fuas_excluded": int((~included_mask).sum()),
        "observed_mapped_followers": int(frame["followers_total"].sum()),
        "selected_follower_denominator": int(round(selected_follower_total)),
        "population_year": int(frame["population_year"].iloc[0]),
        "log_population_center": log_population_center,
        "intercept_at_centered_log_population": float(coefficients[0]),
        "raw_log_population_intercept": float(
            coefficients[0] - slope * log_population_center
        ),
        "population_exponent_beta": slope,
        "beta_standard_error_hc3": slope_standard_error,
        "beta_ci_low_hc3": float(slope_ci_low),
        "beta_ci_high_hc3": float(slope_ci_high),
        "beta_test_value": 1.0,
        "beta_vs_one_z_hc3": float(slope_z_vs_one),
        "beta_equals_one_p_value_hc3": _two_sided_normal_p(slope_z_vs_one),
        "r_squared_log_scale": float(fit["r_squared"]),
        "rmse_log_scale": float(math.sqrt(float(fit["mse"]))),
        "loocv_rmse_log_scale": float(
            math.sqrt(np.mean(leave_one_out_errors**2))
        ),
        "smearing_factor": smearing_factor,
        "huber_population_exponent_beta": float(huber_coefficients[1]),
        "leave_one_out_beta_min": float(leave_one_out_slopes_array.min()),
        "leave_one_out_beta_max": float(leave_one_out_slopes_array.max()),
        "beta_without_london": beta_without_london,
        "most_influential_city": str(
            included.iloc[most_influential_position]["study_city_label"]
        ),
        "largest_cooks_distance": float(
            np.asarray(fit["cooks_distance"])[most_influential_position]
        ),
        "converged": True,
    }
    return results, summary


def _format_population_tick(value: float, _: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}m"
    if value >= 1_000:
        return f"{value / 1_000:g}k"
    return f"{value:g}"


def _format_share_tick(value: float, _: int) -> str:
    if value < 0.0001:
        return f"{value:.3%}"
    if value < 0.001:
        return f"{value:.2%}"
    if value < 0.01:
        return f"{value:.1%}"
    return f"{value:.0%}"


def _mapped_band_bubble_area(value: float) -> float:
    """Keep one-band cities visible while compressing the 1-to-299 range."""

    if value < 0:
        raise ValueError("Mapped-band count cannot be negative")
    return 34.0 * math.sqrt(value)


def _save_chart(
    fig: plt.Figure,
    output_dir: Path,
    filename: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    fig.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=HOUSE["page"],
    )
    plt.show()
    return output_path


def plot_negative_binomial_fit(
    results: pd.DataFrame,
    summary: dict[str, float | int | str | bool],
    *,
    snapshot_date: str,
    output_dir: Path,
    filename: str = "chart_01_negative_binomial_fit.png",
) -> Path:
    """Plot observed and NB2-expected mapped band counts."""

    apply_chart_style()
    ordered = results.sort_values("population")
    fig, ax = plt.subplots(figsize=(11.2, 7.2))

    zero = results["band_count"].eq(0)
    single = results["band_count"].eq(1)
    multiple = results["band_count"].ge(2)
    ax.scatter(
        results.loc[zero, "population"],
        results.loc[zero, "band_count"],
        marker="x",
        s=34,
        color=HOUSE["secondary"],
        linewidth=1.0,
        label="Zero-band cities",
        zorder=4,
    )
    ax.scatter(
        results.loc[single, "population"],
        results.loc[single, "band_count"],
        s=55,
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.2,
        label="Single-band cities",
        zorder=4,
    )
    ax.scatter(
        results.loc[multiple, "population"],
        results.loc[multiple, "band_count"],
        s=65,
        facecolor=HOUSE["blue_soft"],
        edgecolor=HOUSE["blue"],
        linewidth=1.0,
        label="Multi-band cities",
        zorder=4,
    )
    ax.fill_between(
        ordered["population"],
        ordered["expected_count_mean_ci_low"],
        ordered["expected_count_mean_ci_high"],
        color=HOUSE["rule"],
        alpha=0.45,
        linewidth=0,
        label="95% fitted-mean interval",
        zorder=1,
    )
    ax.plot(
        ordered["population"],
        ordered["expected_band_count"],
        color=HOUSE["ink_soft"],
        linewidth=1.8,
        label="Negative-binomial expectation",
        zorder=3,
    )

    focal_cities = {
        "London",
        "Manchester",
        "Liverpool",
        "Sheffield",
        "Birmingham",
        "Leeds",
        "Brighton and Hove",
    }
    extremes = set(
        results.nlargest(2, "pearson_residual")["study_city_label"]
    ) | set(results.nsmallest(2, "pearson_residual")["study_city_label"])
    label_offsets = {
        "Brighton and Hove": (8, 8),
        "Liverpool": (8, 8),
        "Manchester": (8, 8),
        "Birmingham": (8, -13),
        "Leeds": (8, -20),
        "Aberdeen": (-12, 12),
        "Portsmouth": (8, 9),
    }
    for row in results.loc[
        results["study_city_label"].isin(focal_cities | extremes)
    ].itertuples(index=False):
        offset = label_offsets.get(row.study_city_label, (6, 6))
        ax.annotate(
            row.study_city_label,
            (row.population, row.band_count),
            xytext=offset,
            textcoords="offset points",
            ha=("right" if row.study_city_label == "Aberdeen" else "left"),
            fontsize=8.8,
            color=HOUSE["ink_soft"],
            bbox={
                "boxstyle": "round,pad=0.12",
                "facecolor": HOUSE["page"],
                "edgecolor": "none",
                "alpha": 0.82,
            },
        )

    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=1.0, linscale=0.8)
    ax.set_ylim(-0.08, 520)
    ax.set_yticks([0, 1, 3, 10, 30, 100, 300])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.xaxis.set_major_formatter(FuncFormatter(_format_population_tick))
    ax.set_xlabel("FUA population · 2024 · log scale")
    ax.set_ylabel("Mapped bands in the frozen top 1,000 · symlog scale")
    ax.grid(True, which="major")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", ncol=2)
    ax.set_title(
        "Mapped top-1,000 band count versus FUA population",
        loc="left",
        pad=35,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.018,
        (
            f"83 UK FUAs · Spotify snapshot {snapshot_date} · "
            f"NB2 log-link β = {float(summary['population_exponent_beta']):.2f} "
            f"(95% CI {float(summary['beta_ci_low']):.2f}–"
            f"{float(summary['beta_ci_high']):.2f})"
        ),
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    fig.text(
        0.085,
        0.015,
        (
            "Expected counts allocate the 660 mapped bands, not all 1,000 selected "
            "bands; unresolved and excluded origins are not redistributed."
        ),
        color=HOUSE["secondary"],
        fontsize=8.5,
    )
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.14, top=0.84)
    return _save_chart(fig, output_dir, filename)


def plot_negative_binomial_residuals(
    results: pd.DataFrame,
    *,
    output_dir: Path,
    filename: str = "chart_02_negative_binomial_residuals.png",
) -> Path:
    """Plot the largest positive and negative standardized count residuals."""

    apply_chart_style()
    extremes = pd.concat(
        [
            results.nlargest(6, "pearson_residual"),
            results.nsmallest(6, "pearson_residual"),
        ]
    ).drop_duplicates("fua_code")
    extremes = extremes.sort_values("pearson_residual")
    fig, ax = plt.subplots(figsize=(10.4, 6.8))
    colors = [
        HOUSE["blue"] if value >= 0 else HOUSE["gray_blue"]
        for value in extremes["pearson_residual"]
    ]
    y_positions = np.arange(len(extremes))
    ax.hlines(
        y_positions,
        0,
        extremes["pearson_residual"],
        color=HOUSE["rule"],
        linewidth=1.2,
    )
    ax.scatter(
        extremes["pearson_residual"],
        y_positions,
        s=62,
        color=colors,
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.6,
        zorder=3,
    )
    for y_position, row in zip(y_positions, extremes.itertuples(index=False)):
        ax.annotate(
            f"{int(row.band_count)} observed · {row.expected_band_count:.1f} expected",
            (row.pearson_residual, y_position),
            xytext=(6 if row.pearson_residual >= 0 else -6, 0),
            textcoords="offset points",
            ha="left" if row.pearson_residual >= 0 else "right",
            va="center",
            fontsize=8.5,
            color=HOUSE["secondary"],
        )
    ax.axvline(0, color=HOUSE["ink_soft"], linewidth=1.0)
    ax.set_yticks(y_positions, extremes["study_city_label"])
    max_abs = float(np.abs(extremes["pearson_residual"]).max())
    ax.set_xlim(-max_abs * 1.45, max_abs * 1.45)
    ax.set_xlabel("Pearson residual · positive means more bands than expected")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title(
        "Largest negative-binomial count residuals",
        loc="left",
        pad=35,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.018,
        "Six largest positive and negative deviations · NB2 variance-standardized",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    fig.subplots_adjust(left=0.20, right=0.82, bottom=0.12, top=0.83)
    return _save_chart(fig, output_dir, filename)


def plot_loglog_follower_fit(
    results: pd.DataFrame,
    summary: dict[str, float | int | str | bool],
    *,
    snapshot_date: str,
    output_dir: Path,
    filename: str = "chart_01_loglog_follower_fit.png",
) -> Path:
    """Plot follower share against population share with fitted scaling line."""

    apply_chart_style()
    positive = results.loc[results["model_included"]].copy()
    ordered = positive.sort_values("population_share")
    selected_follower_total = float(summary["selected_follower_denominator"])
    expected_share = ordered["expected_follower_median"] / selected_follower_total
    expected_low = ordered["expected_median_ci_low"] / selected_follower_total
    expected_high = ordered["expected_median_ci_high"] / selected_follower_total
    bubble_sizes = positive["band_count"].map(_mapped_band_bubble_area)

    fig, ax = plt.subplots(figsize=(11.2, 7.2))
    multiple = positive["band_count"].ge(2)
    single = positive["band_count"].eq(1)
    ax.scatter(
        positive.loc[multiple, "population_share"],
        positive.loc[multiple, "follower_share"],
        s=bubble_sizes.loc[multiple],
        facecolor=HOUSE["blue_soft"],
        edgecolor=HOUSE["blue"],
        linewidth=1.0,
        alpha=0.9,
        label="Multi-band cities",
        zorder=4,
    )
    ax.scatter(
        positive.loc[single, "population_share"],
        positive.loc[single, "follower_share"],
        s=bubble_sizes.loc[single],
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.2,
        label="Single-band cities",
        zorder=4,
    )
    ax.fill_between(
        ordered["population_share"],
        expected_low,
        expected_high,
        color=HOUSE["rule"],
        alpha=0.45,
        linewidth=0,
        label="95% fitted-median interval",
        zorder=1,
    )
    ax.plot(
        ordered["population_share"],
        expected_share,
        color=HOUSE["ink_soft"],
        linewidth=1.9,
        label="Log–log fitted relationship",
        zorder=3,
    )

    all_values = np.concatenate(
        [positive["population_share"].to_numpy(), positive["follower_share"].to_numpy()]
    )
    lower = 10 ** math.floor(math.log10(float(all_values.min()) * 0.7))
    upper = 1.0
    parity = np.geomspace(lower, upper, 200)
    ax.plot(
        parity,
        parity,
        linestyle=(0, (4, 4)),
        color=HOUSE["secondary"],
        linewidth=1.2,
        label="1:1 proportional-output line",
        zorder=2,
    )

    focal_cities = {
        "London",
        "Manchester",
        "Liverpool",
        "Sheffield",
        "Birmingham",
        "Leeds",
        "Oxford",
        "Crawley",
    }
    extremes = set(
        positive.nlargest(2, "studentized_log_residual")["study_city_label"]
    ) | set(
        positive.nsmallest(2, "studentized_log_residual")["study_city_label"]
    )
    for row in positive.loc[
        positive["study_city_label"].isin(focal_cities | extremes)
    ].itertuples(index=False):
        ax.annotate(
            row.study_city_label,
            (row.population_share, row.follower_share),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8.8,
            color=(
                HOUSE["warning"] if row.band_count == 1 else HOUSE["ink_soft"]
            ),
            bbox={
                "boxstyle": "round,pad=0.12",
                "facecolor": HOUSE["page"],
                "edgecolor": "none",
                "alpha": 0.82,
            },
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lower, upper)
    ax.set_ylim(lower, upper)
    ax.xaxis.set_major_formatter(FuncFormatter(_format_share_tick))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_share_tick))
    ax.set_xlabel("Share of population across all 83 UK FUAs · 2024 · log scale")
    ax.set_ylabel("Share of followers across the selected top-1,000 bands · log scale")
    ax.grid(True, which="major")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    count_references = [1, 10, 50, 300]
    add_superposed_bubble_legend(
        ax,
        title="Bubble area · mapped bands",
        areas=[
            _mapped_band_bubble_area(value) for value in count_references
        ],
        labels=[f"{value}" for value in count_references],
        items=[
            {
                "kind": "marker",
                "label": "Multi-band cities",
                "facecolor": HOUSE["blue_soft"],
                "edgecolor": HOUSE["blue"],
            },
            {
                "kind": "marker",
                "label": "Single-band cities",
                "facecolor": HOUSE["page"],
                "edgecolor": HOUSE["warning"],
            },
            {
                "kind": "patch",
                "label": "95% fitted-median interval",
                "facecolor": HOUSE["rule"],
                "alpha": 0.45,
            },
            {
                "kind": "line",
                "label": "Log–log fitted relationship",
                "color": HOUSE["ink_soft"],
                "linewidth": 1.9,
            },
            {
                "kind": "line",
                "label": "1:1 proportional-output line",
                "color": HOUSE["secondary"],
                "linewidth": 1.2,
                "linestyle": (0, (4, 4)),
            },
        ],
        item_columns=2,
        loc="upper left",
    )
    ax.set_title(
        "Follower output versus population: parity and fitted scaling",
        loc="left",
        pad=35,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.018,
        (
            f"61 positive-output FUAs · Spotify snapshot {snapshot_date} · "
            f"HC3 β = {float(summary['population_exponent_beta']):.2f} "
            f"(95% CI {float(summary['beta_ci_low_hc3']):.2f}–"
            f"{float(summary['beta_ci_high_hc3']):.2f}) · "
            "bubble area is scaled by mapped-band count"
        ),
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    fig.text(
        0.085,
        0.015,
        (
            "The regression excludes 22 zero-output FUAs because log(0) is undefined. "
            "The solid line is a fitted conditional median; the dashed line is parity."
        ),
        color=HOUSE["secondary"],
        fontsize=8.5,
    )
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.14, top=0.84)
    return _save_chart(fig, output_dir, filename)


def plot_loglog_follower_residuals(
    results: pd.DataFrame,
    *,
    output_dir: Path,
    filename: str = "chart_02_loglog_follower_residuals.png",
) -> Path:
    """Plot the largest positive and negative studentized log residuals."""

    apply_chart_style()
    positive = results.loc[results["model_included"]].copy()
    extremes = pd.concat(
        [
            positive.nlargest(6, "studentized_log_residual"),
            positive.nsmallest(6, "studentized_log_residual"),
        ]
    ).drop_duplicates("fua_code")
    extremes = extremes.sort_values("studentized_log_residual")
    fig, ax = plt.subplots(figsize=(10.4, 6.8))
    colors = [
        HOUSE["blue"] if value >= 0 else HOUSE["gray_blue"]
        for value in extremes["studentized_log_residual"]
    ]
    y_positions = np.arange(len(extremes))
    ax.hlines(
        y_positions,
        0,
        extremes["studentized_log_residual"],
        color=HOUSE["rule"],
        linewidth=1.2,
    )
    ax.scatter(
        extremes["studentized_log_residual"],
        y_positions,
        s=62,
        color=colors,
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.6,
        zorder=3,
    )
    for y_position, row in zip(y_positions, extremes.itertuples(index=False)):
        multiple_text = (
            f"{row.observed_to_expected_median:.1f}"
            if row.observed_to_expected_median >= 1
            else f"{row.observed_to_expected_median:.2f}"
        )
        ax.annotate(
            f"{multiple_text}× fitted median",
            (row.studentized_log_residual, y_position),
            xytext=(6 if row.studentized_log_residual >= 0 else -6, 0),
            textcoords="offset points",
            ha="left" if row.studentized_log_residual >= 0 else "right",
            va="center",
            fontsize=8.5,
            color=HOUSE["secondary"],
        )
    ax.axvline(0, color=HOUSE["ink_soft"], linewidth=1.0)
    ax.set_yticks(y_positions, extremes["study_city_label"])
    max_abs = float(np.abs(extremes["studentized_log_residual"]).max())
    ax.set_xlim(-max_abs * 1.45, max_abs * 1.45)
    ax.set_xlabel("Studentized log residual · positive means more followers than fitted")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title(
        "Largest log–log follower residuals",
        loc="left",
        pad=35,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.018,
        "Six largest positive and negative deviations · 61 positive-output FUAs",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    fig.subplots_adjust(left=0.20, right=0.82, bottom=0.12, top=0.83)
    return _save_chart(fig, output_dir, filename)
