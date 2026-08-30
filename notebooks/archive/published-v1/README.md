# Published analysis v1

This directory preserves the original reader-facing 50-band publication.
It uses the Spotify metrics snapshot from 20 September 2025, a manually
curated five-band-per-city shortlist, a 100,000-follower threshold and each
city's top three eligible bands.

It was superseded on 18 July 2026 by the balanced 100-band analysis under
`notebooks/final/`. The archive remains part of the project record and should
not be treated as the current leading result.

Archived charts are under `artifacts/archive/published-v1/`. Rebuild this
version into a separate `rebuild/` subdirectory without touching either the
archived original or the canonical final notebook and charts:

```bash
mkdir -p notebooks/archive/published-v1/rebuild
cp notebooks/archive/published-v1/uk_bands_punching_above_weight.ipynb \
  notebooks/archive/published-v1/rebuild/
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace notebooks/archive/published-v1/rebuild/uk_bands_punching_above_weight.ipynb \
  --ExecutePreprocessor.timeout=180
```
