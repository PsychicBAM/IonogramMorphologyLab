# Security Architecture

The application is local-first. Trust boundaries are: untrusted imported MAT/YAML/rule-pack content; workspace/project artifacts; optional MATLAB backend; exported reports; and local configuration. Parsing should validate schemas and sizes, avoid unsafe loaders, constrain paths to approved locations, and preserve source files as read-only inputs.

Controls include safe YAML loading, no default telemetry, provenance manifests, separation of source and derived data, hygiene scanning for secrets/absolute paths, and CI grep checks for dangerous APIs. The system does not provide multi-user authorization, encryption-at-rest, endpoint protection, or a guarantee that a hostile local user cannot access their own files. Deploy under institutional controls where those properties are required.
