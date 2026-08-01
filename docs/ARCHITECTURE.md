# Architecture

The application is a local PySide6 desktop client. `app/` owns startup and settings; `ui/` presents pages; import/project modules own source references and manifests; analysis and rule modules produce candidate evidence; reporting exports derived artifacts. `matlab_studio/` is optional and isolated behind backends. Rule packs and instrument profiles are versioned data, not executable plug-ins.

Source MAT files are input-only in normal workflows. Workspaces contain project metadata, derived cache, results, logs and exports. Provenance flows from input fingerprint and profile through processing version, method/rule configuration and expert decision. UI code must not silently turn candidate output into a confirmed physical claim.
