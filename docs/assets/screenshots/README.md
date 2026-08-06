# Screenshot Assets (PNG)

Documentation **screenshots** are PNG captures from the live Qt UI using **synthetic teaching data only**. They contain no real user paths, usernames, restricted ionograms, tokens, or personal information.

Schematic **layout mocks** (SVG) live in [`../schematics/`](../schematics/) — those are not screenshots.

## Current README set (ML-A.1a.2)

Directory: [`ml-a1a2/`](ml-a1a2/)

| File | Description |
|------|-------------|
| `home_en.png` / `home_ru.png` | Home dashboard with recommended workflow |
| `ionogram_viewer_en.png` / `ionogram_viewer_ru.png` | Ionogram viewer |
| `campaigns_en.png` / `campaigns_ru.png` | Expert Review Campaigns |
| `expert_review_en.png` / `expert_review_ru.png` | Expert Review Corpora |
| `disagreement_analysis_en.png` / `disagreement_analysis_ru.png` | Disagreement Analysis |
| `ml_data_readiness_en.png` / `ml_data_readiness_ru.png` | ML Data Readiness |
| `results_en.png` / `results_ru.png` | Results |

Total: **14** PNG files (7 screens × EN/RU), 1600×900. See [`ml-a1a2/CAPTURE_LOG.md`](ml-a1a2/CAPTURE_LOG.md).

Root READMEs (`README.md`, `README_RU.md`) use this set.

## Historical page gallery (v1.1.1)

Directory: [`v1.1.1/`](v1.1.1/)

Older full-page tour (36+ PNGs) retained for secondary docs (`CUSTOM_RULE_BUILDER_*`, archive guides). Do not delete while those references remain.

## Regenerate

Preferred for ML-A.1a.2 README set: ephemeral capture under a local workspace (not committed), writing into `docs/assets/screenshots/ml-a1a2/`.

Legacy full-gallery script (writes `v1.1.1/`):

```bash
python scripts/capture_release_screenshots.py
```

## Usage in markdown

From repository root README:

```markdown
![Home (English)](docs/assets/screenshots/ml-a1a2/home_en.png)
```

From `docs/*.md`:

```markdown
![Home](../assets/screenshots/ml-a1a2/home_ru.png)
```
