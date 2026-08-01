# Security Policy

## Supported versions
Security fixes are prepared for the current 1.1.x line. Earlier releases may receive guidance but are not guaranteed patches.

## Reporting a vulnerability
Do not open a public issue for a suspected vulnerability or disclose sensitive sample data. Send a private report to the repository maintainers (configure the repository security advisory contact before public release) with: affected version, reproduction steps, impact, and a minimal non-sensitive proof of concept. We acknowledge reports within 7 days and aim to provide a triage decision within 30 days.

## Scope and boundaries
Relevant issues include unsafe handling of MAT/YAML/rule-pack imports, path traversal, report injection, unsafe subprocess execution, accidental telemetry, secrets committed to the repository, and access-control failures in Protected Scientific Study workflows. The desktop application is designed for local analysis; it is not a multi-user security boundary or a replacement for institutional data controls.

## Handling
Maintainers reproduce privately, assess impact, prepare a fix and regression test, coordinate disclosure, then publish release notes without exposing confidential data. Do not include participant identifiers, restricted ionograms, credentials, or proprietary datasets in reports.
