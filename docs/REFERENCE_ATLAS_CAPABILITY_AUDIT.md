# Reference Atlas Capability Audit — default install

**Pack:** `knowledge_base/REFERENCE_ATLAS_CASES.csv` (REF001–REF009)  
**Loader:** `reference_atlas/atlas.py`  
**Policy:** `docs/REFERENCE_ATLAS_POLICY_EN.md` / `REFERENCE_ATLAS_POLICY_RU.md`

## Executive summary

| Capability | Default install status |
|------------|------------------------|
| Citation metadata | **Yes** — authors, pages, terminology, domain notes |
| Comparison images bundled | **No** — all cases `internal_image_availability` ≠ `available` |
| Image registration / pixel similarity in batch | **No** — `find_nearest()` uses terminology + soft descriptor scores only |
| Rights to redistribute figures | **No** — `rights_status` is metadata-only / copyright-restricted |
| Automatic physical-event matching | **No** — wording is “structurally similar to…”, not “same event” |

Validator: `scripts/validate_reference_atlas.py` (expects ≥5 cases; equatorial domain restrictions enforced).

---

## How similarity works (default path)

When `ReferenceAtlas.find_nearest()` runs after RuleEngine (`projects/pipeline.py`):

1. **Canonical terminology boost** — cases matching `candidate_morphology` score higher.
2. **Soft feature scores** — e.g. `median_horizontal_width`, `median_vertical_width`, `mixed_width_score` when morphology aligns.
3. **Regime penalty** — mismatch with default `user_regime="midlatitude"` reduces score.
4. **Registration confidence** — set to `0.0` when `internal_image_availability != "available"` (all default cases).

The module `similarity/compare.py` implements full image comparison (NCC, SSIM, mask IoU, Hausdorff, …) for **optional** workflows when two comparable arrays and axes exist. It is **not** used by default atlas matching when images are unavailable.

---

## Per-case audit

### REF001 — mixed (Panchenko et al. 2018, A3L018 p.241)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable`) |
| **Comparable instrument** | **Limited** — source DPS-4; user data often Cyclone `Amp_all` |
| **Axes / preprocessing** | **Limited** — source nominal/virtual-height semantics; not Amp_all metrology |
| **Similarity method** | Terminology + soft width features; **not** image registration |
| **Rights** | `journal_copyright_metadata_only` — metadata-only |

### REF002 — frequency (Panchenko et al. 2018, A3L018 p.241)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable`) |
| **Comparable instrument** | **Limited** — DPS-4 vs local archive |
| **Axes / preprocessing** | **Limited** — dFs-style scores not transferable as Amp_all MHz bins |
| **Similarity method** | Terminology + horizontal-width soft score |
| **Rights** | Metadata-only |

### REF003 — range (Panchenko et al. 2018, A3L018 p.241)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable`) |
| **Comparable instrument** | **Limited** — DPS-4 observational context |
| **Axes / preprocessing** | **Limited** — nominal vs true height applies |
| **Similarity method** | Terminology + vertical-width soft score |
| **Rights** | Metadata-only |

### REF004 — frequency taxonomy collage (Benchawattananon et al. 2024, A3L006 Fig.1)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable_in_default_install`) |
| **Comparable instrument** | **Limited** — “various ionogram images”; mixed regimes |
| **Axes / preprocessing** | **Limited** — taxonomy not identical to Article 2; Kazan identity not assumed |
| **Similarity method** | Terminology metadata; optional local CC BY pack may add images (user responsibility) |
| **Rights** | `cc_by_4_0_metadata_preferred` — default install metadata-only |

### REF005 — range / RSF (Benchawattananon et al. 2024, A3L006 Fig.1 RSF)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable_in_default_install`) |
| **Comparable instrument** | **Limited** — mixed regimes |
| **Axes / preprocessing** | **Limited** — mapped with caution to Article 2 range |
| **Similarity method** | Terminology + soft features |
| **Rights** | Metadata-only in default install |

### REF006 — mixed / MSF (Benchawattananon et al. 2024, A3L006 Fig.1 MSF)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable_in_default_install`) |
| **Comparable instrument** | **Limited** — mixed regimes |
| **Axes / preprocessing** | **Limited** — caution mapping to project mixed definition |
| **Similarity method** | Terminology + `mixed_width_score` soft feature |
| **Rights** | Metadata-only in default install |

### REF007 — indeterminate / O-X axis guidance (ИПГ 2008, A3L007 p.14–17)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable`) |
| **Comparable instrument** | **N/A** — VS theory / axis interpretation, not morphology atlas |
| **Axes / preprocessing** | Used for **limitations** (virtual height, O/X), not pixel match |
| **Similarity method** | Citation for ambiguity/layer limitations only |
| **Rights** | `copyright_metadata_only` |

### REF008 — other / monitoring examples (Котонаева ed. 2019, A3L014 ~p.34 Fig.6)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable`) |
| **Comparable instrument** | **Limited** — monitoring collection, mixed context |
| **Axes / preprocessing** | **Limited** — not a dedicated SF morphology atlas |
| **Similarity method** | Citation only |
| **Rights** | Metadata-only; copyrighted source |

### REF009 — other / equatorial SF (Calvert 1962, A3L015)

| Field | Value |
|-------|-------|
| **Image available (default install)** | **No** (`unavailable_in_default_install`) |
| **Comparable instrument** | **Not comparable** to Kazan midlatitude archive for causal transfer |
| **Axes / preprocessing** | Equatorial regime — **C04** forbids direct Kazan transfer |
| **Similarity method** | Historical terminology only; domain mismatch warning when regime differs |
| **Rights** | Metadata-only in default install |

---

## User-imported reference examples

Users may add **legally usable local** comparison images or extended atlas packs outside the default CSV, provided rights are documented. Such imports are **not** expert-validated by the product.

Governance for **owner / expert labels** on approved local frames:

| Module path | Purpose |
|-------------|---------|
| `review_dataset/` | Default root `app_root()/review_dataset/` — JSON label store |
| `review_dataset/store.py` | `ReviewDatasetStore` — add/list/export labels |
| `scripts/init_review_dataset.py` | Initialize workspace layout |

### Review states (`review_dataset/schema.py`)

| State | Meaning |
|-------|---------|
| `unverified` | Imported or draft label; not reviewed |
| `owner-reviewed` | Default for stored labels; project owner assertion |
| `expert-confirmed` | Expert explicitly confirmed; still not “independent external validation” of the whole product |

Labels record separate axes: morphology, layer, interference, ambiguity, quality. Article 3 blinded study paths are **refused** by `assert_allowed_review_source()`.

Optional atlas image packs and review labels do **not** change default batch logic unless separately integrated; default pipeline remains RuleEngine + metadata atlas matching.

---

## Limitations statement (default install)

- No redistributed copyrighted ionogram figures.
- No claim that nearest reference case proves the same ionospheric event.
- Instrument profile mismatch (e.g. `user-defined-unverified`) triggers disagreement flags (`outside_reference_domain`, `instrument_domain_mismatch`).
- Full pixel similarity requires comparable shapes, axes, and user-supplied reference arrays — absent in default atlas pack.
