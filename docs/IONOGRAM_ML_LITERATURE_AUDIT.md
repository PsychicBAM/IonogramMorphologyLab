# Ionogram ML Literature Audit (Post–Phase 4C.4a)

**Date:** 2026-08-06
**Project:** Ionogram Morphology Lab
**Build Identity at audit time:** `4C.4a` (roadmap stage ML-A implemented in `ML-A.1`)
**Branch:** `phase/4c4a-disagreement-analysis`
**Mode:** documentation-only audit (shadow-only product posture unchanged)
**Git:** no commit, no push
**PDFs:** inspected from the owner’s local literature folder outside this repository (`Статьи/`); **not copied into this repository**

This audit informs disagreement-analysis interpretation and future research planning.
It does **not** authorize ML implementation, candidate-rules changes, threshold tuning, or new ML dependencies.

---

## 1. Sources inspected

| ID | Local file (outside repo) | Bibliographic status | Venue / notice |
|----|---------------------------|----------------------|----------------|
| **S2024** | `Earth and Space Science - 2024 - Sherstyukov - A Deep Learning Approach for Automatic Ionogram Parameters Recognition With.pdf` | **Peer-reviewed journal article** | *Earth and Space Science*, 11, e2023EA003446 (2024); DOI 10.1029/2023EA003446; accepted 12 Sep 2024 |
| **P2025?** | `preprint.pdf` | **Non-peer-reviewed preprint** | Explicit banner: —This is a non-peer reviewed preprint submitted to EarthArXivâ€; Castro et al., IGP / Jicamarca–LISN context |

**Title mapping**

- **S2024:** Sherstyukov, Moges, Kozlovsky, Ulich — *A Deep Learning Approach for Automatic Ionogram Parameters Recognition With Convolutional Neural Networks*.
- **P2025?:** Castro, Condor, Scipion, Pacheco — *Deep Learning for Ionogram Parameter Extraction: A Time-Series Approach to Ionospheric Monitoring* (preprint; year not treated as peer-reviewed publication year).

**Important distinction:** claims, error metrics, and operational readiness language in **S2024** carry peer-review status. The same class of claims in **P2025?** must be treated as **provisional** until peer review.

---

## 2. What each paper is actually solving

| Dimension | S2024 (peer-reviewed) | P2025? (preprint) |
|-----------|------------------------|-------------------|
| Primary task | Automatic **URSI-style parameter scaling** (foF2, foF1, foE, foEs, fmin, fbEs, h′F, h′E, h′Es) + layer-presence classification | Automatic **frequency-profile regression** (256-bin height→frequency), then foF2/hmF2 derived |
| Morphology task? | **No** as primary product; Spread-F appears as **complex-case / robustness** context | **No** as taxonomy output; Spread-F is a **contamination / robustness** challenge for scaling |
| Architecture | ResNet50 (+ FC heads); U-Net noise-to-noise prefilter; augmentation | Adapted ResNet units + **LSTM over 5 consecutive ionograms** + Dense |
| Spatial regime | High-latitude polar: Sodankylä (~67°N) | Low-latitude equatorial: Jicamarca VIPIR / LISN |
| Temporal sampling of instrument | Up to 1 ionogram/min in observatory operations; training uses large multi-year archive | Typically 244/day (5 min); some 2024 days at 1440/day |
| Ground truth | Manual operator scaling | Manual SAOExplorer corrections of ARTIST-assisted workflow |

**Implication for IML:** neither paper is a peer-reviewed **Spread-F morphology taxonomy** validator. Both are mainly **parameter-extraction / scaling** studies. IML’s expert morphology corpora and disagreement analysis remain a distinct scientific track.

---

## 3. Dataset design

### 3.1 S2024

- ~**105,000** ionograms with manual ground truth spanning **2008–2021**.
- Training/development used multi-year diversity (solar cycles, seasons, hours).
- Final reported general model: trained on **2008–2020**, tested on **2021**.
- Single station / high-latitude regime.
- Images resized **525×590 → 256×256** (frequency/height pixel scales change accordingly).

### 3.2 P2025?

- **15,520** ionograms from Jicamarca VIPIR only (Tucumán mentioned as available but unused).
- Years/days are **sparse campaign-like selections** (Table 1): selected DOYs in 2017, 2019, 2020, 2022–2024 — not a continuous multi-year census.
- Explicit statement that each day includes at least one Spread-F-affected ionogram (selection bias toward difficult days).
- Input tensors: **5 consecutive ionograms**, each **256×256×2** (O/X), target frequency profile for the **last** frame.
- Labels from SAO after manual correction.

### Audit notes

- S2024: large, year-diverse, high-latitude scaling corpus.
- P2025?: smaller, event-enriched low-latitude corpus with explicit temporal stack inputs.
- Neither corpus matches IML’s mid-latitude Kazan/KFU scientific context by construction; transfer claims would need separate evidence.

---

## 4. Preprocessing

| Topic | S2024 | P2025? |
|-------|-------|--------|
| Resize / grid | Resize to 256×256 | Map to 256×256×2 over 0–22 MHz / 0–1000 km |
| Denoise / filter | Learned **noise-to-noise** U-Net prefilter | Threshold discard &lt;20 dB; clip &gt;50 dB; linearize 0–255 |
| Polarization | Focused on o-mode parameter scaling workflow | Dual O/X channels retained |
| Augmentation | Horizontal/vertical shifts with GT adjustment; batch-time transforms | Gaussian input noise; BN/Dropout/weight regularization |
| Sequence context in input | **Single-image** CNN (no LSTM) | **5-frame** sequence into LSTM |

**Audit notes**

- Preprocessing choices can silently encode station/instrument conventions.
- Any future IML ML path must freeze preprocessing hashes alongside labels (same spirit as IML candidate/snapshot hashes).

---

## 5. Spatial and temporal context

- **S2024** is explicitly polar/high-latitude; authors compare favorably to Autoscala at Sodankylä and note Autoscala is stronger at mid-latitudes.
- **P2025?** is equatorial/low-latitude Spread-F–rich; storm and Spread-F event windows in Jan 2025 are used as post-training checks.
- **Temporal context:**
  - S2024’s strongest methodological lesson is **year-separated testing** (see §7).
  - P2025? explicitly argues that operators already use **previous ionograms** when correcting foF2 under Spread-F, motivating LSTM.
- **For IML:** mid-latitude morphology disagreement analysis should not import polar scaling RMSE or equatorial Spread-F profile MAE as if they were morphology accuracy.

---

## 6. Spread-F handling

### 6.1 S2024

- Not a Spread-F classifier paper.
- Literature review cites Lan/Rao-style Spread-F **classification** accuracies from other works.
- Complex-case section includes frequency Spread-F and range Spread-F examples.
- Reports that foF2 absolute-error statistics under Spread-F conditions (table column foF2(SF)) remain comparable; some hard cases still produce large foF2 disagreements when vertical vs oblique / Spread-F interpretation diverges from the operator.
- Ambiguous operator–model disputes are acknowledged (including F1 nighttime presence disputes).

### 6.2 P2025?

- Spread-F is central motivation: ARTIST struggles; manual correction uses temporal continuity.
- Class language used in results: clear / FSF / RSF / SSF (and related).
- Model outputs a continuous frequency profile rather than a morphology class label.
- Claims improved robustness on Spread-F / storm windows, but as a **preprint**.

### Audit notes for IML morphology

- Parameter-scaling robustness under Spread-F ≠ correct morphology class assignment.
- IML's mixed/frequency/range/indeterminate taxonomy and assessability/interference axes remain necessary even if a scaler —looks goodâ€ on foF2.

---

## 7. Validation splitting, independent-year testing, and leakage

### 7.1 What S2024 shows (critical for IML)

During method development, validation samples were **randomly selected from the same year range as training**. The authors observed:

- validation errors looked optimistic;
- **independent 2021 test** errors were higher;
- reason given: same-year validation ionograms **resemble training shapes**.

They conclude explicitly that reliable evaluation requires a test set from a **different year** than training.

This is the central literature lesson for IML holdout design.

### 7.2 What P2025? reports

- Split described as **80% train / 20% test** (and validation loss curves shown).
- Exact split unit (random ionogram vs day vs sequence block) is **not clearly specified** in the extracted text.
- Later —new dataâ€ from weeks after training (Jan 2025 storm/Spread-F events) is a valuable **temporal external check**, but does not replace a pre-registered year/sequence holdout protocol.
- Because inputs are 5-frame windows, random frame-level splitting can place **overlapping sequences** into both train and test unless blocked by date/sequence rules.

### 7.3 Risk of randomly splitting neighboring ionograms

Neighboring ionograms (seconds–minutes apart) share:

- the same geophysical state evolution,
- similar noise/instrument fingerprints,
- often the same Spread-F episode,
- correlated operator decisions.

Therefore:

1. **Random frame-level splits inflate apparent performance** (same-year / neighbor leakage).
2. **Sequence-aware models (LSTM)** are especially vulnerable if windows overlap across splits.
3. **Morphology labels** in IML are likewise temporally correlated; random split of adjacent frames is scientifically unsafe for future ML or ruleset evaluation.

### 7.4 IML-aligned holdout principles reinforced by this audit

Prefer separation by:

- source date / acquisition period,
- sequence identity,
- related-frame group,
- campaign / year block,

and forbid:

- random neighbor-frame splits between development and untouched holdout,
- treating development-exposed disagreement items as independent holdout.

---

## 8. Complex cases, reproducibility, interpretability

| Theme | S2024 | P2025? |
|-------|-------|--------|
| Complex cases | Dedicated section (gaps, weak traces, z/o/x, cusps/hooks, FSF/RSF, blanketing Es) | Focused on Spread-F and storm intervals; profile overlays vs SAO |
| Reproducibility | Zenodo data/models DOI; GitHub software link; SGO data portal | HDF5 dataset mentioned; preprint status; less archival certainty than S2024 |
| Interpretability | Limited (CNN); residual blocks; case studies vs operator | Limited (CNN+LSTM); profile visualization vs ARTIST/manual |
| Operator disagreement | Explicitly discusses disputable F1 / Spread-F interpretation cases | Motivates temporal operator workflow; less formal disagreement ontology |

**Audit notes**

- Both papers treat operator labels as training targets; neither solves expert–model disagreement governance.
- IML Phase 4C.4a disagreement analysis is the correct place to record descriptive transitions and hypotheses **without** declaring ground truth.

---

## 9. Implications for Ionogram Morphology Lab

### A. Current disagreement analysis (Phase 4C.4a)

1. Keep disagreement analysis **descriptive only**; do not import S2024/P2025? RMSE/F-score language as morphology accuracy.
2. Use literature as **hypothesis fuel** (e.g., mixed↔frequency transitions may reflect definition ambiguity or oblique/vertical interpretation), not as automatic ruleset changes.
3. Stratify descriptive views by assessability, interference, source/date, and candidate evidence — analogous to literature emphasis on hard cases.
4. Prefer sequence/date-aware case grouping in the explorer; avoid interpreting adjacent-frame repeats as independent evidence.
5. **Contamination statement (binding):** all items frozen into the current disagreement-analysis snapshots are **development-exposed**. They **must not** be described as untouched independent holdout data for evaluating a future modified ruleset or future ML model.

### B. Future ruleset work

1. Outcome F (or equivalent) may justify a **separate proposal phase** only after an untouched holdout plan exists.
2. Literature supports investigating upstream geometry/evidence and label-definition issues before parameter-tuning fantasies.
3. Do **not** retune candidate thresholds because a polar scaler or equatorial LSTM profile model reports low foF2 error.
4. Any future ruleset evaluation must use **non-overlapping** sequences/dates relative to development-exposed disagreement items.

### C. Future ML research (not implemented now)

1. Parameter-scaling ML (S2024/P2025?) and morphology-class ML are different products; do not conflate them.
2. If morphology ML is ever pursued, require year/sequence-aware holdout from day one.
3. Sequence models need explicit anti-leakage rules for sliding windows.
4. Mid-latitude transfer from Sodankylä or Jicamarca models is an unproven research claim for IML.
5. No ML dependencies and no training are introduced by this audit.

---

## 10. Future ML roadmap (ML-A…ML-E) — planning only

**ML-A…ML-E is a research planning roadmap.** Phase **ML-A.1** implements the **ML-A** stage (readiness audit + Gate). Phase **ML-B.1** implements the **ML-B** stage as immutable identity manifests and leakage-safe role reservation (still no training, no ML runtime dependencies, no RuleEngine wiring, no accuracy/F1 claims). Stages **ML-C…ML-E** remain future planning and are **not** authorized by ML-B.1.

Preserved governance concepts across all stages:

- problem and label contracts before any experiment;
- descriptive disagreement analysis (not ground truth);
- **Decision Gate** before experimental modification paths;
- items marked `development_exposed` **cannot** enter an untouched holdout;
- no production RuleEngine wiring from ML;
- no morphology accuracy / F1 / sensitivity / specificity claims without a valid reference-standard protocol and untouched holdout evaluation.

### ML-A — Dataset and Label Readiness Audit

- Separate morphology taxonomy, parameter scaling, assessability, interference, and expert-decision contracts.
- Audit label volume, class coverage, source/date coverage, missingness, disagreement, and reviewer independence.
- **No training.**

### ML-B — Immutable Dataset Manifests and Leakage-Safe Splits

- Immutable train, development, and untouched holdout manifests.
- Separation by year/date, sequence, related-frame group, and campaign.
- Contamination registry (including exclusion of development-exposed disagreement items from untouched holdout).
- Preprocessing and source hashes.
- Zero train / development / holdout overlap (item identity, related-frame group, and sequence where available).

### ML-C — Offline Experimental Baselines

- Experiments **outside** the production RuleEngine.
- Start with simple candidate-independent features and/or image baselines.
- Pre-registered metrics and denominators.
- Development data only.
- No production wiring and **no holdout reveal**.

### ML-D — Temporal Sequence Experiment

- CNN-LSTM or another justified temporal architecture.
- Neighboring ionograms grouped as sequences.
- Sliding windows must **never** cross dataset partitions.
- Compare against the offline single-frame baseline from ML-C.
- Development data only.

### ML-E — Independent Untouched Holdout Evaluation

- Run only after architecture and analysis protocol are frozen.
- Evaluate **once** on the untouched date/sequence-aware holdout.
- Record exact model, preprocessing, dataset, and environment hashes.
- No claim upgrade without independent scientific review.
- No automatic production deployment.

---

## 11. Crosswalk: literature lessons → IML controls already present

| Literature lesson | IML control (4C.4a / prior phases) |
|-------------------|-------------------------------------|
| Same-year / neighbor leakage inflates scores | Holdout overlap checks; related-frame/sequence separation; campaign sampling warnings |
| Independent-year testing is more honest | Prefer acquisition-period / date-block holdouts in Decision Gate planning |
| Spread-F is hard and definition-sensitive | Morphology labels + assessability + interference axes; disagreement matrix is descriptive |
| Operator labels are not absolute truth | Scientifically validated = false; candidate ≠ ground truth; Decision Gate outcomes A–F |
| Inspecting data contaminates future evaluation | `development_exposed` contamination tracking |

---

## 12. Explicit non-actions of this audit

- No ML model implemented.
- No candidate rules, thresholds, geometry versions, or engine versions changed.
- No ML libraries added.
- No PDFs copied into the repository.
- No full pytest rerun (documentation-only task).
- No commit / no push.

---

## 13. Summary judgment

1. **S2024** is the stronger methodological reference for **validation hygiene**: it demonstrates, in peer-reviewed text, that random same-year validation can look deceptively good and that **independent-year testing** is required.
2. **P2025?** is a useful **non-peer-reviewed** argument for **temporal context** (multi-ionogram LSTM) under equatorial Spread-F, but its 80/20 split description is insufficiently leakage-proof as written and must not be copied as IML policy.
3. For IML, the immediate operational consequence is already aligned with Phase 4C.4a: treat disagreement analysis as descriptive, mark inspected items development-exposed, and require untouched sequence/date-aware holdouts before any future ruleset or ML evaluation path.
