# Data directory

- `raw/` contains timestamped source responses. Keep promoted inputs and records
  needed for an audit; remove incomplete retries once their cause is understood.
- `interim/` contains reviewable pipeline output that is not yet canonical.
- `processed/` contains analysis-ready inputs and outputs.
- `snapshots/` contains checksummed rollback points for canonical inputs. Use
  this instead of creating separate backup directories.

For repeated experiments, retain the latest complete run and any deliberately
named milestone. Do not keep every failed or superseded attempt.

The canonical top-100 popularity-first FUA experiment uses:

- `processed/popularity_first_top100_20260718T204522Z_population_strict.csv`
  for the conservative origin-to-FUA result;
- `processed/popularity_first_top100_20260718T204522Z_population_extended.csv`
  for the reviewed boundary sensitivity;
- `interim/popularity_first_top100_20260718T204522Z_fua_mapping_audit.csv`
  for the band-level denominator audit.

Both views retain band counts alongside rates because one-band FUAs are
especially sensitive to a single globally dominant act.

The executed canonical notebook is
`notebooks/experiments/snapshots/uk_bands_top100_popularity_first_fua_20260718T204522Z.ipynb`.
The earlier raw-only and population-adjusted companion notebooks remain
preserved as predecessor branches.
