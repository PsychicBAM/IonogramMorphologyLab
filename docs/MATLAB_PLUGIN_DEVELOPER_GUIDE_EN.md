# MATLAB Plugin Developer Guide

## Contract
A MATLAB Studio plugin is a MATLAB/Octave script plus an `.iml-matlab.yaml` manifest. Plugins extend a project through the registry; they do not require edits to the application source. The registry validates a manifest before registration and supports load, enable, disable, and persisted status.

## Manifest
Required practical fields are `plugin_id`, bilingual names, `entrypoint`, `script_type`, `scientific_status`, and a positive `timeout`. Script types include frame, sequence, file/folder analysis, rendering, feature extraction, classifier, comparison, export, teaching demo, and custom. Scientific statuses distinguish `built_in_verified`, project-verified, user-tested, imported-unverified, disabled, example, and teaching content. Never label imported code verified without independent evidence.

```yaml
plugin_id: ridge_metrics_v1
name_en: Ridge metrics
name_ru: Метрики трека
entrypoint: ridge_metrics.m
script_type: feature_extraction
scientific_status: imported_unverified
timeout: 120
Octave_compatible: true
```

## Bridge design
Use only the documented `iml_*` helpers. Treat bridge input matrices as read-only. Put artifacts in the supplied run workspace, use unique names, and register output features or candidate results rather than silently relying on workspace variables. Include parameter values, algorithm revision, input scope, limits, and warnings in provenance.

## Execution and isolation
The runner creates an isolated working directory and copies the entry script. It captures stdout/stderr, output files, errors, and elapsed time. A plugin must tolerate a missing backend, cancelled work, and an unavailable optional toolbox. Do not assume that a MATLAB Engine session exists; external MATLAB and Octave are different backends.

## Testing checklist
Validate the manifest; register it in a temporary registry; verify enable/disable persistence; run against a tiny synthetic matrix when a backend is installed; inspect a `none` backend result; and verify source-MAT hashes remain unchanged. Test failure paths, not just a successful script.

## Scientific and security responsibilities
Plugin authors own interpretation claims. A registered feature is not validated solely by registration. Preserve abstention, quality flags, alternative explanations, and uncertainty. Do not access protected study material unless the optional Protected Scientific Study mode is deliberately enabled and configured.
