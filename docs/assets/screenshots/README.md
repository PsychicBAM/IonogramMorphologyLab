# Screenshot Assets (PNG)

Documentation **screenshots** are PNG captures from the live Qt UI using **synthetic teaching data only** (`synthetic_data/`, EvidenceQA workspace). They contain no real user paths, usernames, restricted ionograms, tokens, or personal information.

Schematic **layout mocks** (SVG) live in [`../schematics/`](../schematics/) — those are not screenshots.

## Regenerate PNG captures

```bash
python scripts/capture_release_screenshots.py
```

Requires PySide6 and a display or offscreen Qt platform. The script moves legacy SVG mocks to `docs/assets/schematics/` automatically.

See [`CAPTURE_LOG.md`](CAPTURE_LOG.md) for the latest capture metadata.

## PNG inventory (v1.1.1)

| File | Description |
|------|-------------|
| `home_en.png` / `home_ru.png` | Home dashboard with recommended workflow |
| `project_creation_en.png` / `project_creation_ru.png` | New project dialog / flow |
| `mat_import_en.png` / `mat_import_ru.png` | Import Data page |
| `data_audit_en.png` / `data_audit_ru.png` | Data Audit summary |
| `instrument_profile_en.png` / `instrument_profile_ru.png` | Instrument profile |
| `ionogram_viewer_en.png` / `ionogram_viewer_ru.png` | Ionogram viewer |
| `contact_sheet_en.png` / `contact_sheet_ru.png` | Contact sheet builder |
| `batch_analysis_en.png` / `batch_analysis_ru.png` | Batch analysis |
| `results_en.png` / `results_ru.png` | Results table |
| `expert_review_en.png` / `expert_review_ru.png` | Expert review |
| `rule_builder_en.png` / `rule_builder_ru.png` | Rule Builder wizard |
| `rule_testing_en.png` / `rule_testing_ru.png` | Rule Testing Lab |
| `matlab_studio_en.png` / `matlab_studio_ru.png` | MATLAB Studio |
| `method_comparison_en.png` / `method_comparison_ru.png` | Method comparison |
| `pipeline_builder_en.png` / `pipeline_builder_ru.png` | Pipeline builder |
| `parameters_en.png` / `parameters_ru.png` | Ionogram parameters |
| `settings_en.png` / `settings_ru.png` | Settings |
| `help_en.png` / `help_ru.png` | Help search |

Total: **36** PNG files (18 screens × EN/RU).

## Usage in markdown

From repository root README:

```markdown
![Home (English)](docs/assets/screenshots/home_en.png)
```

From `docs/*.md`:

```markdown
![Home](../assets/screenshots/home_ru.png)
```
