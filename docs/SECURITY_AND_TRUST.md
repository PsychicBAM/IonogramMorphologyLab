# Security and Trust — Ionogram Morphology Lab 1.1.1

## Security reporting

Report vulnerabilities privately as described in [SECURITY.md](../SECURITY.md). Do not include credentials, restricted ionograms, participant identifiers, or proprietary datasets in public issues.

## Trust boundaries

- Source MAT data is an input and remains read-only in normal workflows.
- Imported rule packs, MATLAB scripts, model artifacts, and project packages may be untrusted; inspect and validate them before use.
- The application is local-first and has no telemetry enabled by default.
- Local file paths and provenance data can appear in reports; review exports before sharing.
- IML is not a multi-user access-control boundary and does not replace institutional controls, encryption, or record signing.

## Scientific trust

Application results are candidates, not confirmed mechanisms or calibrated measurements. A passed software test or synthetic-data QA is not a scientific-validation claim. See the [Scientific Guide](SCIENTIFIC_GUIDE_EN.md) and [Scientific Classification QA](SCIENTIFIC_CLASSIFICATION_QA.md).

## Technical references

- [Security policy](../SECURITY.md)
- [Threat model](THREAT_MODEL.md)
- [Security architecture](SECURITY_ARCHITECTURE.md)
- [Dependency audit](DEPENDENCY_AUDIT_V1_1_1.md)
