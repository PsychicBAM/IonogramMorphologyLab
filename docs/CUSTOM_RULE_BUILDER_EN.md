# Custom Rule Builder — No-Code Wizard

**Version:** 1.1.1  
**Audience:** analysts and method developers who need **versioned, source-linked** morphology rules without writing Python.

The **Rule Builder** creates local `ScientificRule` definitions stored as YAML under your project or user library. A saved rule is a **candidate evidence procedure** — not validated science until you test it under your protocol.

> **Honest scope:** The wizard generates predicates and optional code **previews**. Passing the wizard or generating MATLAB/Python text does **not** imply peer review, operational approval, or universal accuracy across stations.

## When to use Rule Builder

| Use Rule Builder when… | Use something else when… |
|------------------------|---------------------------|
| You have a documented threshold or feature condition from literature | You need a black-box ML classifier → **Model Lab** (development only) |
| You want bilingual metadata and provenance fields | You need one-off manual labels → **Expert Review** |
| You will test against a labelled development set | You have no labels yet → collect expert review first |
| You need to disable obsolete rules without erasing history | You want to delete audit trail → not supported by design |

## Concepts

| Term | Meaning |
|------|---------|
| **Rule ID** | Stable identifier (e.g. `spread_f_width_candidate`) — do not reuse for different logic |
| **Target axis** | One of layer, morphology, ambiguity, quality, interference, parameter — **one primary target per rule** |
| **Condition** | Feature + operator + threshold + units |
| **Abstention / exclusion** | Explicit path when evidence is insufficient |
| **Status** | `draft`, `project_approved`, `source_verified`, etc. — strict pipelines filter on this |
| **Version** | Each save creates a new versioned snapshot |

## Wizard workflow (step by step)

### 1. Open Rule Builder

From **Home** (Expert mode) or the navigation menu → **Rule Builder** → **New rule**.

The intro panel explains purpose, when to use the page, and risks (e.g. mixing axes).

![Rule Builder wizard](../assets/screenshots/rule_builder_en.png)

*Alt: Rule Builder no-code wizard with condition preview.*

### 2. Identity and target

Fill in:

- **Rule ID** — lowercase snake_case, stable across versions;
- **Names** (EN and RU) — human-readable titles;
- **Target axis** — pick exactly one primary scientific axis;
- **Proposed result** — token emitted when the rule fires (not a physical mechanism claim);
- **Layer / morphology context** — keep distinct from quality or interference rules.

**Example (illustrative only):**

| Field | Example value |
|-------|---------------|
| Rule ID | `candidate_spread_f_band` |
| Target axis | morphology |
| Proposed result | `spread_f_candidate` |

### 3. Conditions

Add one or more conditions:

| Element | Guidance |
|---------|----------|
| **Feature** | Must exist in the feature registry for your profile (width, spacing, SNR proxy, etc.) |
| **Operator** | `gte`, `lte`, `eq`, `between`, … as exposed in UI |
| **Threshold** | Numeric with **units** documented in the rule |
| **Logic** | AND across conditions unless advanced tab specifies otherwise |

Define **abstention**: what happens when features are missing or quality is below threshold.

Define **exclusions**: profiles, modes, or interference states where the rule must not fire.

### 4. Applicability and provenance

Complete:

- **Instrument profiles** or domains where the rule applies;
- **Alternatives** considered in the source literature;
- **Assumptions** (scaling, trace picking, preprocessing);
- **Limitations** (known failure modes);
- **Source identifiers and pages** — bibliographic traceability;
- **Verification status** — start as `draft`; upgrade only with review records.

Statuses like `source_verified` or `project_approved` must be backed by **documented review**, not by wizard completion alone.

### 5. Preview generated code

Select **Preview generated code** (Advanced tab may show Python and MATLAB emitters).

Inspect:

- human-readable condition summary;
- generated predicate function;
- abstention branches.

Generated code is for **inspection and external review** — the application does not treat it as endorsed science.

### 6. Save rule

Select **Save rule**. The store writes a **versioned** YAML snapshot. Duplicate rule IDs with conflicting content are handled through versioning — review history before enabling in strict mode.

### 7. Test in Rule Testing Lab

Before production use:

1. Open **Rule Testing Lab**.
2. Load an **eligible labelled set** (CSV or project frames with expert labels).
3. Run **threshold sweep** and **confusion vs labels** on development data only.
4. Review false positives on ambiguous and negative cases.
5. Document split method (e.g. by date — never leak neighboring frames across train/test).

See [Rule testing guide](RULE_TESTING_GUIDE_EN.md).

### 8. Export or install pack (optional)

- **Export pack** — ZIP with `pack.yaml` and `rules/*.yaml` for sharing.
- **Import pack** — only from trusted authors; v1.1.1 rejects unsafe ZIP paths and oversize archives.

Installed packs live under the application user library; disable obsolete rules instead of deleting provenance.

## UX modes

| Mode | Rule Builder visibility |
|------|-------------------------|
| Guided | Hidden or deferred — switch to Research/Expert on Home |
| Research | Visible; wizard emphasized |
| Expert | Full tabs including Advanced code preview |

## Quality checklist

Before marking a rule `project_approved`:

- [ ] Units on every numeric threshold
- [ ] Profile/domain constraints documented
- [ ] Exclusions for known interference modes
- [ ] Bibliographic source IDs and pages
- [ ] Negative and ambiguous cases in Rule Testing Lab
- [ ] Limitations paragraph completed
- [ ] Abstention path tested (missing features)
- [ ] EN and RU names reviewed by a bilingual reviewer if reports are bilingual

Synthetic examples in the bundled library demonstrate **implementation behavior only**.

## Strict vs permissive rule filtering

Pipeline settings may filter rules by status:

| Filter | Behavior |
|--------|----------|
| Permissive | Draft rules may fire with warnings |
| Scientific strict | Only `source_verified` (or configured approved set) |

Do not enable strict mode until testing records exist.

## Security notes

- Import rule packs only from trusted ZIP files — see [Threat model](THREAT_MODEL.md).
- YAML is loaded with `yaml.safe_load`; do not manually merge untrusted YAML into rule directories.
- Generated MATLAB/Python is **user-inspectable text** — treat like any script before external execution.

## Related documentation

- [Rule testing guide](RULE_TESTING_GUIDE_EN.md)
- [Morphology methods](MORPHOLOGY_METHODS_EN.md)
- [Scientific limitations](SCIENTIFIC_LIMITATIONS_EN.md)
- [Quick start](QUICK_START_EN.md)
