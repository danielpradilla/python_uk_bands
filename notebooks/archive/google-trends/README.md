# Google Trends archive

These notebooks are preserved exploratory work. They are not part of the active analysis pipeline.

The approach was abandoned because Google Trends values are sampled and normalized within each request. Comparing many bands required anchoring and batching choices that made the resulting city scores difficult to defend. The saved CSVs remain beside the notebooks so the historical work can still be inspected.

The current project uses saved Spotify metrics and built-up-area populations instead. See [`../../final/uk_bands_punching_above_weight.ipynb`](../../final/uk_bands_punching_above_weight.ipynb).

To rerun the archived notebooks from the repository root, install their local
requirements:

```bash
python -m pip install -r notebooks/archive/google-trends/requirements.txt
```

Those extra plotting and Google Trends packages are intentionally excluded from
the active environment.
