# Threat Model — 1.1.1

**Scope:** Ionogram Morphology Lab as a **local desktop** application processing user-selected ionogram data, YAML/JSON configuration, ZIP archives (rule packs and project packages), optional MATLAB/Octave backends, and exported reports.

**Assumptions:** The OS account boundary is intact. Users may intentionally run their own scripts. The application is **not** a multi-user security boundary, HSM, or scientific truth oracle.

**Non-goals:** Institutional authorization, encryption-at-rest, endpoint protection, cryptographic signing of scientific records, or proof of correctness on hostile workstations.

**Review triggers:** New parsers, network features, executable plug-ins, archive formats, authentication, cloud sync, or autoload of remote content.

---

## Threat inventory

| Threat | Attack surface | Impact | Current control | Test / evidence | Residual risk | User action |
|--------|----------------|--------|-----------------|-----------------|---------------|-------------|
| **Untrusted MAT / HDF5** | Import Data, SciPy/h5py readers, variable selection | Crash, excessive memory/disk, mis-audit leading to wrong science | User-selected paths only; Data Audit surfaces dimensions; source MAT read-only in normal flow; failed import aborts without overwriting source | Import/integration tests on synthetic MAT; manual audit of v5/v7 and v7.3 teaching fixtures | Parser/library defects; crafted files not in test corpus; local disk exhaustion on huge arrays | Import only authorized copies; cap batch scope; review Data Audit before analysis |
| **Untrusted YAML** | Instrument profiles, rule definitions, pack manifests, MATLAB manifests | Logic abuse via unexpected types; denial of service via huge documents | `yaml.safe_load` in audited paths (`instrument_profiles`, `rule_builder.packs`, `matlab_studio.manifest`); schema validation via dataclasses / required fields | Grep CI forbids `yaml.load(`; pack validation tests | Validation gaps on new keys; CPU/memory on very large YAML | Trust rule packs and profiles from known authors; review diffs before install |
| **Untrusted JSON** | `project.json`, settings import/export, frame prediction JSON, SQLite payload columns | Type confusion, unexpected keys affecting UI or pipeline | `json.loads` with explicit field access; settings merged through known keys | Project/portability tests | New code paths may trust extra keys without schema | Do not merge untrusted JSON into production projects without review |
| **Rule pack ZIP (general)** | Rule Builder → import pack | Install malicious or malformed rules | ZIP opened read-only; extract to temp dir; `install_pack` copies into `user_library/rule_packs/<pack_id>` only after validation | `validate_pack` on bundled core pack; `import_pack` regression tests | Bug in validation could allow bad rules (not RCE by themselves) | Install packs from trusted sources; disable rules instead of deleting provenance |
| **ZIP slip (path traversal)** | `import_pack`, `import_project_package` | Write outside target directory → overwrite files or plant scripts | `import_pack`: `_unsafe_zip_name` rejects `..`, absolute, rooted, drive/UNC paths before extract. `import_project_package`: `_safe_members` resolves each member under destination root | `test_rule_packs_are_valid_and_broken_archives_are_isolated` rejects `../escape.txt` | Future archive features must copy the same pattern | Do not import archives from untrusted email/web downloads without inspection |
| **Symlinks in archives** | `import_pack` on Unix-style ZIP external attrs | Redirect extract to sensitive paths | Reject entries whose Unix mode indicates symlink (`0o120000`) | Code review; extend tests on Unix CI when available | Windows-specific symlink attributes may differ; not all archive tools set attrs consistently | Prefer exporting packs from this application; scan archives on Unix before import |
| **Path traversal (non-ZIP)** | Manual pack directory install, workspace paths | Read/write unintended files | Pack install from directory uses fixed `installed_packs_dir()`; project operations anchor on user-chosen project root | Hygiene script blocks absolute paths in docs/src | User can still point project at sensitive directories they own | Keep projects in dedicated workspace folders |
| **Oversized decompression (zip bomb)** | `import_pack` | Memory/disk exhaustion | Limits: 500 entries, 25 MiB compressed, 80 MiB total uncompressed, 10 MiB per entry | Limits enforced before `extractall` | Other ZIP entry points (`export_project_package`, MATLAB library export) are write-only from trusted local tree | Reject unexpectedly large downloads; monitor disk during import |
| **SQLite project DB** | `project.sqlite` in project root | Tampered metadata, audit log poisoning, denial of service | Standard library SQLite; JSON columns; no arbitrary SQL from UI; large matrices **not** stored in DB | DB used in pipeline/project tests | Attacker with filesystem access can edit DB directly; not integrity-signed | Protect project folder permissions; treat copied projects as untrusted |
| **MATLAB scripts / plugins** | MATLAB Studio import, `.m` library, bundled examples | Arbitrary code execution when user runs scripts | Scripts copied into project/library with hash/version records; execution requires explicit user action and configured backend; manifests document dependencies | Backend tests skipped when MATLAB absent | **User-invoked MATLAB/Octave is equivalent to running untrusted code** | Review `.m` files before run; use isolated VM/account for unknown scripts |
| **Subprocess invocation** | MATLAB/Octave external backend, hygiene/validation scripts | Command injection if paths interpolated into shell | `subprocess.run` with **argument list**, `shell=False` (default); CI grep forbids `shell=True` in `src/` and `scripts/` | Static grep in `security.yml`; runner uses list form `[exe, "-batch", ...]` | MATLAB `-batch` string still embeds workspace path — malicious path names could confuse quoting (mitigated by resolved absolute POSIX path with quote escape) | Avoid bizarre path characters; prefer simple workspace paths |
| **Environment injection** | External MATLAB/Octave, Python child processes | Inherited env vars alter behavior | No documented env-based autoload of remote config; subprocess inherits OS env | Manual review of `runner.py`, `backends.py` | User-controlled `PATH` can redirect `matlab`/`octave` binary | Use known-good installs; verify `which matlab` before enabling Studio |
| **Pickle / joblib** | Model Lab `model.joblib` load/save | Arbitrary code execution on load of malicious artifact | No direct `pickle.` in `src/`; joblib used only for **project-local** models user trained or copied | Grep CI; model cards warn development-only | **joblib uses pickle** — copied `model.joblib` from untrusted source is dangerous | Never load foreign joblib files; treat models like executable code |
| **HTML injection** | Report HTML export | XSS if HTML opened in browser with scripts | `_md_to_simple_html` applies `html.escape` to line content and title/lang attributes | Code review of `export_reports.py` | Markdown source not HTML-sanitized for `<script>` if raw HTML inserted into records in future | Open reports offline; treat exported HTML like untrusted documents if sharing |
| **Markdown injection** | Report `.md` export, bibliography | Misleading rendering in viewers that execute HTML | Markdown built from structured fields; frame IDs in backticks | Export tests | Viewers that render raw HTML in MD may still mis-display crafted expert text | Review expert rationale fields before publication |
| **Logs with private paths** | UI report log, run records, MATLAB diary paths | Unintentional disclosure of usernames/paths in shared screenshots or exports | Logs reflect user-selected paths by design; hygiene docs warn reviewers | Repository hygiene rejects absolute paths in committed docs | Runtime logs in project folder contain real paths | Redact before sharing; use synthetic projects for teaching captures |
| **Project package import** | `.imlzip` portable packages | ZIP slip, inclusion of unexpected scripts, relink to attacker path | `_safe_members` containment; default export excludes `*.mat`; relink requires explicit path list from user | `test_portable_package_excludes_source_mat_and_can_relink` | User can opt into `include_source_mat`; relinked paths are user-supplied | Import packages from trusted collaborators; inspect manifest; relink sources deliberately |

---

## Dependency and supply-chain (cross-cutting)

| Threat | Attack surface | Impact | Current control | Test / evidence | Residual risk | User action |
|--------|----------------|--------|-----------------|-----------------|---------------|-------------|
| **Vulnerable dependencies** | numpy, scipy, h5py, Pillow, Jinja2, PyYAML, etc. | Known CVEs in parsers/renderers | Pinned minimums in `pyproject.toml`; `pip-audit` in release process; Bandit when installed in CI | `security.yml` workflow | Transitive advisories may exceed audit cadence; not all CVEs are reachable from app code paths | Keep venv updated; review [Security audit v1.1.1](SECURITY_AUDIT_V1_1_1.md) |
| **Secrets in repository** | Committed tokens, API keys | Credential leak | `.gitignore`; hygiene regex scan on tracked text files | `check_repository_hygiene.py` in CI | False negatives; secrets in binary files | Never commit credentials; rotate if leaked |
| **Malicious pull request** | GitHub Actions | Workflow token abuse | Least-privilege workflows; no secrets in fork PR jobs; static checks | `security.yml`, `test.yml` | Hosted runner supply-chain risk | Maintainer review for workflow changes |

---

## Severity guidance (for triage)

| Level | Meaning in IML context |
|-------|------------------------|
| **Critical** | Unauthenticated remote RCE with default install — **out of scope** (local app, no default network listener) |
| **High** | Default workflow executes untrusted code or writes outside project without user action |
| **Medium** | User-triggered import/archive flaw, joblib load of untrusted file, dependency CVE with plausible reachability |
| **Low** | Disclosure of local paths, denial of service on crafted input, integrity of unsigned local SQLite |
| **Info** | Hardening opportunities, documentation gaps, CI tool availability |

See [SECURITY.md](../SECURITY.md) for private reporting and [SECURITY_AUDIT_V1_1_1.md](SECURITY_AUDIT_V1_1_1.md) for the v1.1.1 audit record.
