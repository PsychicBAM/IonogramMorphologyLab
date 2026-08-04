# Rule Testing Guide — 1.1.1

Use **Rule Testing Lab** to evaluate rule **implementation behavior** and empirical metrics on a labelled development set. Passing a lab test is **not** independent scientific validation.

## Before you test

Prepare a dataset with documented:

- data source and usage permissions;
- class definitions and labelling protocol;
- instrument profile coverage;
- reviewer identity and date range;
- known ambiguous or negative cases.

Never tune thresholds on blinded evaluation data unless your protocol explicitly permits it.

## Workflow

1. **Select rule version** — confirm rule ID, status, and YAML version in the project or library.
2. **Select labelled dataset** — CSV export or in-project frames with expert labels.
3. **Declare split method** before viewing metrics (e.g. by date block — avoid leaking neighboring frames across train/test).
4. **Choose metrics** appropriate to the target axis: accuracy alone is insufficient when abstention is allowed; review confusion matrix and subgroup failures.
5. **Threshold sweep** — optional; document chosen operating point separately from exploration runs.
6. **Run test** — inspect false positives, false negatives, and indeterminate/abstained cases in **Viewer**.
7. **Export run record** — include dataset fingerprint, split, rule version, settings, and limitations paragraph.

## Interpreting results

| Observation | Likely action |
|-------------|---------------|
| High FP on ambiguous O/X cases | Add exclusions or abstention; do not deploy in strict mode |
| Missing features for many frames | Fix profile or feature registry coverage |
| Good metrics on synthetic only | Repeat on station-specific dev set before claims |
| Identical train/test file | Invalid validation — redesign split |

## Strict pipeline interaction

When **scientific strict** filtering is enabled, only approved/verified rule statuses run in production batches. Complete Rule Testing Lab records before promoting status.

## Security and data handling

- Import rule packs only from trusted ZIP sources ([Threat model](THREAT_MODEL.md)).
- Redact local paths from exported test reports shared externally.
- Do not attach restricted ionograms to public bug reports.

## Reporting in publications

Describe:

- rule ID and version hash;
- label provenance and inter-reviewer agreement if available;
- split design and excluded epochs;
- abstention rate and failure modes;
- explicit statement that results are **development evidence**, not multi-station validation.

## Related documentation

- [Custom Rule Builder](CUSTOM_RULE_BUILDER_EN.md)
- [Morphology methods](MORPHOLOGY_METHODS_EN.md)
- [Scientific Guide](SCIENTIFIC_GUIDE_EN.md)
- [Troubleshooting](TROUBLESHOOTING_EN.md)
