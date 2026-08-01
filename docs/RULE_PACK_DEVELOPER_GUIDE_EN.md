# Rule Pack Developer Guide

## Package structure
Place each pack under `rule_packs/<pack-id>/` with:

```text
pack.yaml
rules/<rule-id>.yaml
README_EN.md
README_RU.md
```

`pack.yaml` requires `pack_id` and `version`. Each rule is loaded as a `ScientificRule`; unknown fields are ignored for forward compatibility, but required scientific metadata should never be omitted merely to make a pack load.

## Authoring rules
Keep layer, morphology, ambiguity, quality, and parameter outputs separate. Include applicability, excluded conditions, alternatives, limitations, source identifiers, printed/PDF pages, threshold origin, and verification/implementation status. Do not invent Es letter subtypes: use only source-traceable entries from `ES_SUBTYPE_SOURCE_REGISTRY.csv`.

## Validation and installation
Run `validate_pack()` before distribution. Importing a ZIP checks for unsafe absolute or traversal paths and isolates broken archives. A failed import must not alter installed packs. Test enable/disable behavior against a temporary installed-pack directory.

## Status filtering
Scientific Strict uses `filter_rules_by_status()` and should expose only the supported approved/source-verified statuses. A pack author must not promote a rule merely because it runs, agrees with another method, or passes a synthetic test.

## Reproducibility
Version rules, document changes, preserve references and rights notes, and record feature definitions and profile domains. State clearly that threshold sweeps and synthetic data are development checks, not scientific validation.
