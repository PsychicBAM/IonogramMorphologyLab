# Plugin Architecture

The project uses data-driven extension points: instrument profiles, rule packs, MATLAB method manifests and pipeline configurations. They are parsed as constrained data and must not execute arbitrary code on import. Each extension should declare identifier, version, compatibility, provenance, applicability, limitations and verification status.

Validate an extension before installation, store it in a controlled project/user library, and retain its exact version in reports. Native executable or Python plug-ins are not a supported trust boundary in 1.1.1; review code changes through the normal source process.
