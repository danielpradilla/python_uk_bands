#!/usr/bin/env python3
"""Build separate top-1000 negative-binomial and log-log notebooks."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import nbformat as nbf
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.output_share import build_output_share_metrics  # noqa: E402
from python_uk_bands.scaling_models import (  # noqa: E402
    fit_loglog_follower_scaling,
    fit_negative_binomial_band_scaling,
)


DEFAULT_SNAPSHOT_ID = "20260718T204522Z"
DEFAULT_POPULATION_SNAPSHOT_ID = "20260718T201304Z"
DEFAULT_TOP_N = 1000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", default=DEFAULT_SNAPSHOT_ID)
    parser.add_argument(
        "--population-snapshot-id",
        default=DEFAULT_POPULATION_SNAPSHOT_ID,
    )
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--force", action="store_true")
    return parser


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _base_setup_cell(
    *,
    bands_path: Path,
    mapping_path: Path,
    population_path: Path,
    artifact_dir: Path,
    snapshot_id: str,
    top_n: int,
) -> str:
    return f'''from pathlib import Path
import json

import pandas as pd
from IPython.display import Image, Markdown, display

ROOT = next(
    (
        candidate
        for candidate in (Path.cwd(), *Path.cwd().parents)
        if (candidate / "{_relative(bands_path)}").exists()
    ),
    None,
)
if ROOT is None:
    raise FileNotFoundError("Could not locate the uk-music-cities repository root")

import sys
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.output_share import build_output_share_metrics

SNAPSHOT_ID = "{snapshot_id}"
TOP_N = {top_n}
BANDS_PATH = ROOT / "{_relative(bands_path)}"
MAPPING_AUDIT_PATH = ROOT / "{_relative(mapping_path)}"
POPULATION_PATH = ROOT / "{_relative(population_path)}"
ARTIFACT_DIR = ROOT / "{_relative(artifact_dir)}"

bands = pd.read_csv(BANDS_PATH, keep_default_na=False)
mapping_audit = pd.read_csv(MAPPING_AUDIT_PATH, keep_default_na=False)
population = pd.read_csv(POPULATION_PATH, keep_default_na=False)

shares, coverage = build_output_share_metrics(
    bands,
    mapping_audit,
    population,
    included_tiers={{"strict", "reviewed_extended"}},
)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

assert len(bands) == bands["returned_spotify_id"].nunique() == TOP_N
assert len(mapping_audit) == TOP_N
assert len(shares) == coverage["population_fuas"] == 83
assert coverage["mapped_bands"] == int(shares["band_count"].sum()) == 660
assert coverage["zero_band_fuas"] == int(shares["band_count"].eq(0).sum()) == 22
'''


def _negative_binomial_notebook(
    *,
    bands_path: Path,
    mapping_path: Path,
    population_path: Path,
    artifact_dir: Path,
    snapshot_id: str,
    top_n: int,
    snapshot_date: str,
    summary: dict[str, float | int | str | bool],
    results: pd.DataFrame,
) -> nbf.NotebookNode:
    leader = results.iloc[0]
    liverpool = results.loc[
        results["study_city_label"].eq("Liverpool")
    ].iloc[0]
    cells: list[nbf.NotebookNode] = []
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""# Top-1,000 band counts: negative-binomial population scaling

## tl;dr

This model asks how many **mapped bands from the frozen top 1,000** an FUA has
relative to the count expected from its population.

- The population exponent is **{summary['population_exponent_beta']:.2f}**
  (95% CI **{summary['beta_ci_low']:.2f}–{summary['beta_ci_high']:.2f}**;
  test against proportional scaling `β = 1`, **p = {summary['beta_equals_one_p_value']:.4f}**).
  Band counts therefore rise more than proportionally with population in this
  catalogue.
- The negative-binomial model fits materially better than Poisson on its own
  outcome: AIC **{summary['aic']:.1f}** versus **{summary['poisson_aic']:.1f}**;
  Poisson Pearson dispersion is **{summary['poisson_pearson_dispersion']:.2f}**.
- **{leader['study_city_label']}** has the largest positive standardized
  residual: {int(leader['band_count'])} observed bands versus
  {leader['expected_band_count']:.1f} expected.
- **Liverpool** has {int(liverpool['band_count'])} observed versus
  {liverpool['expected_band_count']:.1f} expected.
- All **83 FUAs** are retained, including **22 zero-band FUAs**.

**Bottom line:** this is the better primary model for **scene breadth** and for
the question “how many selected bands would population predict?” It estimates
expectations for the **660 mapped bands**, not the 340 selected identities whose
origins cannot be allocated to the population universe."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            r"""## 01. Context & Methods

The response is each 2021 UK Functional Urban Area's count of bands in the
frozen popularity-first top-1,000 catalogue that have a strict or
reviewed-extended FUA assignment. The model is an NB2 generalized linear model:

$$
Y_i \sim \operatorname{NB}(\mu_i, \alpha), \qquad
\log(\mu_i) = a + \beta\log(P_i).
$$

The null `β = 1` corresponds to proportional scaling. A positive residual means
the city has more mapped bands than the model expects at its population. The
NB2 variance is $\mu_i + \alpha\mu_i^2$, allowing the clustering that a Poisson
model cannot absorb.

### Key Assumptions

- Counts cover the frozen top 1,000 and the reviewed mapping snapshot, not a
  census of all British bands.
- Unmapped bands remain unallocated; expected counts target the 660 mapped
  observations.
- Current population is compared with bands formed across many decades.
- City residuals are descriptive associations, not causal estimates of what
  population creates."""
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 02. Data"))
    setup = _base_setup_cell(
        bands_path=bands_path,
        mapping_path=mapping_path,
        population_path=population_path,
        artifact_dir=artifact_dir,
        snapshot_id=snapshot_id,
        top_n=top_n,
    )
    setup += '''
coverage_table = pd.DataFrame(
    [
        {"Measure": "Selected bands", "Value": coverage["selected_bands"]},
        {"Measure": "Mapped bands modelled", "Value": coverage["mapped_bands"]},
        {"Measure": "FUAs", "Value": coverage["population_fuas"]},
        {"Measure": "Positive-count FUAs", "Value": coverage["mapped_fuas"]},
        {"Measure": "Zero-count FUAs", "Value": coverage["zero_band_fuas"]},
    ]
)
display(coverage_table.style.hide(axis="index"))
'''
    cells.append(nbf.v4.new_code_cell(setup))
    cells.append(
        nbf.v4.new_markdown_cell(
            "The 83-row FUA frame preserves zero counts. This is the main reason "
            "to prefer a count model over ordinary regression on `log(band_count)`."
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 03. Results"))
    cells.append(
        nbf.v4.new_markdown_cell("### 03.01 Fit the negative-binomial model")
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''from python_uk_bands.scaling_models import (
    fit_negative_binomial_band_scaling,
    plot_negative_binomial_fit,
    plot_negative_binomial_residuals,
)

model_results, model_summary = fit_negative_binomial_band_scaling(shares)
RESULTS_PATH = ARTIFACT_DIR / "negative_binomial_fua_results.csv"
SUMMARY_PATH = ARTIFACT_DIR / "negative_binomial_model_summary.json"
model_results.to_csv(RESULTS_PATH, index=False)
with SUMMARY_PATH.open("w", encoding="utf-8") as handle:
    json.dump(model_summary, handle, indent=2, sort_keys=True)

coefficient_table = pd.DataFrame(
    [
        {
            "Population exponent β": model_summary["population_exponent_beta"],
            "95% CI low": model_summary["beta_ci_low"],
            "95% CI high": model_summary["beta_ci_high"],
            "p-value for β = 1": model_summary["beta_equals_one_p_value"],
            "NB dispersion α": model_summary["dispersion_alpha"],
        }
    ]
)
display(coefficient_table.style.hide(axis="index").format(precision=3))
display(Markdown(f"Saved `{RESULTS_PATH.relative_to(ROOT)}` and `{SUMMARY_PATH.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "### 03.02 Expected counts across the population range"
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            f'''fit_chart_path = plot_negative_binomial_fit(
    model_results,
    model_summary,
    snapshot_date="{snapshot_date}",
    output_dir=ARTIFACT_DIR,
)
display(Image(filename=str(fit_chart_path)))
display(Markdown(f"Exported to `{{fit_chart_path.relative_to(ROOT)}}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "The fitted curve is the expected count under the observed scaling "
            "relationship. The y-axis uses a symlog scale so zero-count cities "
            "remain visible without adding an arbitrary pseudocount."
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell("### 03.03 Which cities depart most from expectation?")
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''residual_chart_path = plot_negative_binomial_residuals(
    model_results,
    output_dir=ARTIFACT_DIR,
)
display(Image(filename=str(residual_chart_path)))
display(Markdown(f"Exported to `{residual_chart_path.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''notable_cities = [
    "London", "Manchester", "Liverpool", "Sheffield",
    "Birmingham", "Leeds", "Brighton and Hove", "Guildford",
]
notable = (
    model_results.loc[
        model_results["study_city_label"].isin(notable_cities),
        [
            "study_city_label", "population", "band_count",
            "expected_band_count", "observed_to_expected_count",
            "pearson_residual",
        ],
    ]
    .sort_values("pearson_residual", ascending=False)
    .rename(
        columns={
            "study_city_label": "FUA",
            "population": "Population",
            "band_count": "Observed bands",
            "expected_band_count": "Expected bands",
            "observed_to_expected_count": "Observed / expected",
            "pearson_residual": "Pearson residual",
        }
    )
)
display(
    notable.style.hide(axis="index").format(
        {
            "Population": "{:,.0f}",
            "Expected bands": "{:.1f}",
            "Observed / expected": "{:.2f}×",
            "Pearson residual": "{:+.2f}",
        }
    )
)
'''
        )
    )
    cells.append(nbf.v4.new_markdown_cell("### 03.04 Model diagnostics"))
    cells.append(
        nbf.v4.new_code_cell(
            '''diagnostics = pd.DataFrame(
    [
        {"Diagnostic": "Negative-binomial AIC", "Value": model_summary["aic"]},
        {"Diagnostic": "Poisson AIC", "Value": model_summary["poisson_aic"]},
        {"Diagnostic": "Poisson Pearson dispersion", "Value": model_summary["poisson_pearson_dispersion"]},
        {"Diagnostic": "McFadden pseudo-R²", "Value": model_summary["mcfadden_pseudo_r_squared"]},
        {"Diagnostic": "NB optimizer converged", "Value": model_summary["converged"]},
    ]
)
display(diagnostics.style.hide(axis="index").format({"Value": lambda value: f"{value:.3f}" if isinstance(value, float) else str(value)}))

assert model_summary["converged"]
assert model_summary["aic"] < model_summary["poisson_aic"]
assert model_summary["poisson_pearson_dispersion"] > 1
assert abs(model_summary["population_exponent_beta"] - __EXPECTED_BETA__) < 1e-10
assert int(model_results["band_count"].sum()) == coverage["mapped_bands"]
'''.replace("__EXPECTED_BETA__", repr(summary["population_exponent_beta"]))
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 04. Takeaways"))
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""1. **Counts scale superlinearly in this catalogue.** The fitted
   exponent is {summary['population_exponent_beta']:.2f}, and its interval does
   not include proportional scaling at `β = 1`.
2. **Negative binomial is preferable to Poisson.** The AIC improvement and
   Poisson dispersion of {summary['poisson_pearson_dispersion']:.2f} confirm
   meaningful overdispersion.
3. **Expected count is not a recommended catalogue size.** It is the number of
   mapped top-1,000 bands predicted for each FUA given the fixed catalogue.
4. **Residuals are the model-adjusted “punching above weight” measure.** They
   replace the chart's assumed 1:1 baseline with an empirically estimated
   population relationship.
5. **This is the stronger primary model for scene breadth.** The separate
   log–log notebook remains useful for audience reach, but it answers a
   different question and drops zero-output FUAs.

### 04.01 Status

**Share with caveats.** The model is internally validated and retains the full
FUA universe, but catalogue selection, incomplete origin mapping and the
current-versus-historical population mismatch prevent causal or definitive
claims about British music production."""
        )
    )
    return nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
    )


def _loglog_notebook(
    *,
    bands_path: Path,
    mapping_path: Path,
    population_path: Path,
    artifact_dir: Path,
    snapshot_id: str,
    top_n: int,
    snapshot_date: str,
    summary: dict[str, float | int | str | bool],
    results: pd.DataFrame,
) -> nbf.NotebookNode:
    leader = results.loc[results["model_included"]].iloc[0]
    multiplicative_error = math.exp(float(summary["loocv_rmse_log_scale"]))
    cells: list[nbf.NotebookNode] = []
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""# Top-1,000 follower reach: log–log population scaling

## tl;dr

This model asks how mapped top-1,000 **follower totals** scale with FUA
population among places with positive output.

- The population exponent is **{summary['population_exponent_beta']:.2f}**
  with HC3 95% CI **{summary['beta_ci_low_hc3']:.2f}–{summary['beta_ci_high_hc3']:.2f}**
  (`β = 1` test, **p = {summary['beta_equals_one_p_value_hc3']:.4f}**).
  Follower output also scales superlinearly in this catalogue.
- The model explains **{summary['r_squared_log_scale']:.1%}** of log-scale
  variation, but leave-one-out RMSE is **{summary['loocv_rmse_log_scale']:.2f}**
  log points—roughly a **{multiplicative_error:.1f}×** multiplicative error.
- The slope is reasonably stable: Huber regression gives
  **{summary['huber_population_exponent_beta']:.2f}** and leave-one-city-out
  slopes range from **{summary['leave_one_out_beta_min']:.2f}** to
  **{summary['leave_one_out_beta_max']:.2f}**.
- **{leader['study_city_label']}** is the largest positive residual at
  **{leader['observed_to_expected_median']:.1f}×** its fitted median—but it is a
  single-band result, demonstrating the superstar problem.
- The regression uses **61 positive-output FUAs** and necessarily excludes
  **22 zero-output FUAs**.

**Bottom line:** log–log regression is useful for **audience impact and the
shape of scaling**, but it is weaker as the primary city-scene model because it
drops zeros and follower totals can be dominated by one act."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            r"""## 01. Context & Methods

The response is the summed Spotify follower count of mapped bands in each FUA.
The fitted model is:

$$
\log(F_i) = a + \beta\log(P_i) + \epsilon_i.
$$

Ordinary least squares estimates the line; HC3 covariance supplies
heteroskedasticity-robust uncertainty. The null `β = 1` is proportional
scaling. Exponentiating a residual gives the observed follower total relative
to the fitted conditional median. Huber regression and leave-one-city-out
slopes are retained as influence checks.

### Key Assumptions

- Only FUAs with positive mapped follower output can enter an ordinary log–log
  regression; no arbitrary `+1` pseudocount is used.
- Followers are summed artist-level counts with unknown audience overlap.
- Residuals measure global Spotify reach associated with bands assigned to an
  FUA, not local listenership or scene depth.
- Superstar concentration, catalogue selection, mapping coverage and the
  current-versus-historical population mismatch remain material limitations."""
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 02. Data"))
    setup = _base_setup_cell(
        bands_path=bands_path,
        mapping_path=mapping_path,
        population_path=population_path,
        artifact_dir=artifact_dir,
        snapshot_id=snapshot_id,
        top_n=top_n,
    )
    setup += '''
coverage_table = pd.DataFrame(
    [
        {"Measure": "FUAs in population universe", "Value": coverage["population_fuas"]},
        {"Measure": "Positive-output FUAs", "Value": coverage["mapped_fuas"]},
        {"Measure": "Zero-output FUAs excluded from log fit", "Value": coverage["zero_band_fuas"]},
        {"Measure": "Mapped follower share", "Value": coverage["mapped_follower_share"]},
        {"Measure": "Mapped bands", "Value": coverage["mapped_bands"]},
    ]
)
display(
    coverage_table.style.hide(axis="index").format(
        {"Value": lambda value: f"{value:.1%}" if isinstance(value, float) and value < 1 else f"{value:g}"}
    )
)
'''
    cells.append(nbf.v4.new_code_cell(setup))
    cells.append(
        nbf.v4.new_markdown_cell(
            "The fit covers every FUA with at least one mapped band but cannot "
            "represent the 22 zero-output places. This is an explicit selection "
            "condition, not a plotting choice."
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 03. Results"))
    cells.append(nbf.v4.new_markdown_cell("### 03.01 Fit the log–log model"))
    cells.append(
        nbf.v4.new_code_cell(
            '''from python_uk_bands.scaling_models import (
    fit_loglog_follower_scaling,
    plot_loglog_follower_fit,
    plot_loglog_follower_residuals,
)

model_results, model_summary = fit_loglog_follower_scaling(shares)
RESULTS_PATH = ARTIFACT_DIR / "loglog_follower_fua_results.csv"
SUMMARY_PATH = ARTIFACT_DIR / "loglog_follower_model_summary.json"
model_results.to_csv(RESULTS_PATH, index=False)
with SUMMARY_PATH.open("w", encoding="utf-8") as handle:
    json.dump(model_summary, handle, indent=2, sort_keys=True)

coefficient_table = pd.DataFrame(
    [
        {
            "Population exponent β": model_summary["population_exponent_beta"],
            "HC3 95% CI low": model_summary["beta_ci_low_hc3"],
            "HC3 95% CI high": model_summary["beta_ci_high_hc3"],
            "p-value for β = 1": model_summary["beta_equals_one_p_value_hc3"],
            "Huber β": model_summary["huber_population_exponent_beta"],
        }
    ]
)
display(coefficient_table.style.hide(axis="index").format(precision=3))
display(Markdown(f"Saved `{RESULTS_PATH.relative_to(ROOT)}` and `{SUMMARY_PATH.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "### 03.02 Compare parity with the fitted scaling relationship"
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            f'''fit_chart_path = plot_loglog_follower_fit(
    model_results,
    model_summary,
    snapshot_date="{snapshot_date}",
    output_dir=ARTIFACT_DIR,
)
display(Image(filename=str(fit_chart_path)))
display(Markdown(f"Exported to `{{fit_chart_path.relative_to(ROOT)}}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "The dashed line retains the original proportional-output benchmark. "
            "The solid line is the empirically fitted relationship. Because "
            "`β > 1`, the gap between those expectations changes with city size. "
            "Bubble area is scaled by mapped-band count."
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell("### 03.03 Which cities depart most from the fitted line?")
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''residual_chart_path = plot_loglog_follower_residuals(
    model_results,
    output_dir=ARTIFACT_DIR,
)
display(Image(filename=str(residual_chart_path)))
display(Markdown(f"Exported to `{residual_chart_path.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''notable_cities = [
    "London", "Manchester", "Liverpool", "Sheffield",
    "Birmingham", "Leeds", "Oxford", "Crawley",
]
notable = (
    model_results.loc[
        model_results["study_city_label"].isin(notable_cities),
        [
            "study_city_label", "band_count", "followers_total",
            "expected_follower_median", "observed_to_expected_median",
            "studentized_log_residual", "largest_band_follower_share",
        ],
    ]
    .sort_values("studentized_log_residual", ascending=False)
    .rename(
        columns={
            "study_city_label": "FUA",
            "band_count": "Mapped bands",
            "followers_total": "Observed followers",
            "expected_follower_median": "Fitted median",
            "observed_to_expected_median": "Observed / fitted",
            "studentized_log_residual": "Studentized residual",
            "largest_band_follower_share": "Largest-band share",
        }
    )
)
display(
    notable.style.hide(axis="index").format(
        {
            "Observed followers": "{:,.0f}",
            "Fitted median": "{:,.0f}",
            "Observed / fitted": "{:.2f}×",
            "Studentized residual": "{:+.2f}",
            "Largest-band share": "{:.1%}",
        }
    )
)
'''
        )
    )
    cells.append(nbf.v4.new_markdown_cell("### 03.04 Model diagnostics and influence"))
    cells.append(
        nbf.v4.new_code_cell(
            '''diagnostics = pd.DataFrame(
    [
        {"Diagnostic": "Log-scale R²", "Value": model_summary["r_squared_log_scale"]},
        {"Diagnostic": "Log-scale RMSE", "Value": model_summary["rmse_log_scale"]},
        {"Diagnostic": "Leave-one-out log RMSE", "Value": model_summary["loocv_rmse_log_scale"]},
        {"Diagnostic": "Huber population exponent", "Value": model_summary["huber_population_exponent_beta"]},
        {"Diagnostic": "Leave-one-out β minimum", "Value": model_summary["leave_one_out_beta_min"]},
        {"Diagnostic": "Leave-one-out β maximum", "Value": model_summary["leave_one_out_beta_max"]},
        {"Diagnostic": "β without London", "Value": model_summary["beta_without_london"]},
        {"Diagnostic": "Most influential city", "Value": model_summary["most_influential_city"]},
    ]
)
display(diagnostics.style.hide(axis="index").format({"Value": lambda value: f"{value:.3f}" if isinstance(value, float) else str(value)}))

assert model_summary["n_fuas_included"] == 61
assert model_summary["zero_output_fuas_excluded"] == 22
assert abs(model_summary["population_exponent_beta"] - __EXPECTED_BETA__) < 1e-10
assert model_summary["leave_one_out_beta_min"] <= model_summary["population_exponent_beta"] <= model_summary["leave_one_out_beta_max"]
'''.replace("__EXPECTED_BETA__", repr(summary["population_exponent_beta"]))
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 04. Takeaways"))
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""1. **Follower reach scales superlinearly in the positive-output
   subset.** The HC3 interval for `β` is
   {summary['beta_ci_low_hc3']:.2f}–{summary['beta_ci_high_hc3']:.2f}.
2. **The slope is not just a London artifact.** Removing London gives
   `β = {summary['beta_without_london']:.2f}`; Huber regression gives
   `β = {summary['huber_population_exponent_beta']:.2f}`.
3. **City predictions remain noisy.** Leave-one-out log RMSE corresponds to
   roughly {multiplicative_error:.1f}× multiplicative error.
4. **Follower residuals are not scene-depth estimates.** Crawley and several
   other large positive residuals are overwhelmingly or entirely attributable
   to one selected band.
5. **Use this as the audience-impact companion.** The negative-binomial count
   model is better for expected band numbers and includes the whole population
   universe; this model is better for studying how global reach scales among
   represented cities.

### 04.01 Status

**Share with strong caveats.** The exponent and influence checks are
reproducible, but zero-output selection and superstar concentration materially
limit city-level interpretation."""
        )
    )
    return nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.top_n != 1000:
        raise ValueError("These comparison notebooks are intentionally fixed to top 1,000")

    prefix = f"popularity_first_top{args.top_n}_{args.snapshot_id}"
    bands_path = PROJECT_ROOT / "data" / "processed" / f"{prefix}_bands.csv"
    mapping_path = PROJECT_ROOT / "data" / "interim" / f"{prefix}_fua_mapping_audit.csv"
    population_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"uk_fua_population_2021_{args.population_snapshot_id}.csv"
    )
    for path in [bands_path, mapping_path, population_path]:
        if not path.exists():
            raise FileNotFoundError(path)

    bands = pd.read_csv(bands_path, keep_default_na=False)
    mapping = pd.read_csv(mapping_path, keep_default_na=False)
    population = pd.read_csv(population_path, keep_default_na=False)
    if len(bands) != args.top_n or bands["returned_spotify_id"].nunique() != args.top_n:
        raise ValueError("Top-1,000 bands input must contain 1,000 unique identities")

    shares, coverage = build_output_share_metrics(
        bands,
        mapping,
        population,
        included_tiers={"strict", "reviewed_extended"},
    )
    if coverage["mapped_bands"] != 660 or coverage["population_fuas"] != 83:
        raise ValueError("Frozen top-1,000 coverage no longer matches the reviewed snapshot")

    nb_results, nb_summary = fit_negative_binomial_band_scaling(shares)
    log_results, log_summary = fit_loglog_follower_scaling(shares)
    snapshot_date = str(bands.iloc[0]["stats_extracted_at_utc"])[:10]
    artifact_dir = (
        PROJECT_ROOT
        / "artifacts"
        / "experiments"
        / "top1000_scaling_models"
        / args.snapshot_id
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)

    comparison = pd.DataFrame(
        [
            {
                "dimension": "Question",
                "negative_binomial": "How many mapped bands does population predict?",
                "loglog_followers": "How does mapped follower reach scale with population?",
                "assessment": "Different outcomes; AIC is not comparable across them.",
            },
            {
                "dimension": "FUA coverage",
                "negative_binomial": "83/83, including 22 zeros",
                "loglog_followers": "61/83 positive-output FUAs",
                "assessment": "Negative binomial has better population coverage.",
            },
            {
                "dimension": "Population exponent",
                "negative_binomial": f"{nb_summary['population_exponent_beta']:.2f} ({nb_summary['beta_ci_low']:.2f}–{nb_summary['beta_ci_high']:.2f})",
                "loglog_followers": f"{log_summary['population_exponent_beta']:.2f} ({log_summary['beta_ci_low_hc3']:.2f}–{log_summary['beta_ci_high_hc3']:.2f})",
                "assessment": "Both reject proportional scaling in this catalogue.",
            },
            {
                "dimension": "Main vulnerability",
                "negative_binomial": "Unmapped identities and catalogue cutoff",
                "loglog_followers": "Zero exclusion and superstar-dominated totals",
                "assessment": "Follower residuals need stronger concentration caveats.",
            },
            {
                "dimension": "Recommended role",
                "negative_binomial": "Primary model for scene breadth",
                "loglog_followers": "Secondary model for audience impact",
                "assessment": "Negative binomial is better for the stated expected-band question.",
            },
        ]
    )
    comparison.to_csv(artifact_dir / "model_comparison.csv", index=False)

    notebook_dir = PROJECT_ROOT / "notebooks" / "experiments"
    nb_path = notebook_dir / (
        "13_uk_bands_top1000_negative_binomial_scaling.ipynb"
    )
    log_path = notebook_dir / (
        "14_uk_bands_top1000_loglog_follower_scaling.ipynb"
    )
    if not args.force:
        existing = [str(path) for path in [nb_path, log_path] if path.exists()]
        if existing:
            raise FileExistsError(f"Notebooks already exist; pass --force: {existing}")

    nbf.write(
        _negative_binomial_notebook(
            bands_path=bands_path,
            mapping_path=mapping_path,
            population_path=population_path,
            artifact_dir=artifact_dir,
            snapshot_id=args.snapshot_id,
            top_n=args.top_n,
            snapshot_date=snapshot_date,
            summary=nb_summary,
            results=nb_results,
        ),
        nb_path,
    )
    nbf.write(
        _loglog_notebook(
            bands_path=bands_path,
            mapping_path=mapping_path,
            population_path=population_path,
            artifact_dir=artifact_dir,
            snapshot_id=args.snapshot_id,
            top_n=args.top_n,
            snapshot_date=snapshot_date,
            summary=log_summary,
            results=log_results,
        ),
        log_path,
    )
    print(nb_path.relative_to(PROJECT_ROOT))
    print(log_path.relative_to(PROJECT_ROOT))
    print((artifact_dir / "model_comparison.csv").relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
