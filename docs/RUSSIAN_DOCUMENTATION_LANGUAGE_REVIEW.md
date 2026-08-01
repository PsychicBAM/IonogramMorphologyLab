# Russian Documentation Language Review — v1.1.1

**Review date:** 2026-08-01  
**Scope:** User-facing Russian markdown for release 1.1.1 evidence closure  
**Reviewer role:** Documentation hardening pass (UTF-8, terminology, bilingual parity)

---

## Files reviewed

| File | Status | Notes |
|------|--------|-------|
| [README_RU.md](../README_RU.md) | Fixed | Provenance terminology; contamination label; expert codes; PNG screenshots |
| [docs/QUICK_START_RU.md](QUICK_START_RU.md) | Fixed | Expert decision codes glossed; PNG asset links |
| [docs/COMPLETE_USER_MANUAL_RU.md](COMPLETE_USER_MANUAL_RU.md) | Rewritten | Recovered from mojibake; «Учебный пример» 1–10 + Tutorial |
| [docs/INSTALLATION_RU.md](INSTALLATION_RU.md) | Rewritten | Expanded; MATLAB optional |
| [docs/TROUBLESHOOTING_RU.md](TROUBLESHOOTING_RU.md) | Rewritten | Natural technical Russian; UTF-8 |
| [docs/FAQ_RU.md](FAQ_RU.md) | Rewritten | Expert codes table; provenance definition |
| [docs/CUSTOM_RULE_BUILDER_RU.md](CUSTOM_RULE_BUILDER_RU.md) | Updated | PNG screenshot link; retained EN tokens where UI requires |
| [docs/RULE_TESTING_GUIDE_RU.md](RULE_TESTING_GUIDE_RU.md) | Rewritten | Expanded testing protocol wording |
| [docs/MATLAB_STUDIO_GUIDE_RU.md](MATLAB_STUDIO_GUIDE_RU.md) | Expanded | Version 1.1.1; provenance paragraph |
| [docs/SCIENTIFIC_METHOD_RU.md](SCIENTIFIC_METHOD_RU.md) | Expanded | Axis table; abstention policy |
| [docs/USABILITY_QA_RU.md](USABILITY_QA_RU.md) | Verified | Already UTF-8 clean in source tree |

---

## Fix categories applied

### Mojibake and encoding

- Recovered corrupted Cyrillic in `COMPLETE_USER_MANUAL_RU.md`, `TROUBLESHOOTING_RU.md`, `INSTALLATION_RU.md`, `FAQ_RU.md`, and related guides with valid UTF-8 Russian prose translated from English sources.
- Confirmed files save as UTF-8 without Latin-1 fallback characters.

### Terminology

| Issue | Resolution |
|-------|------------|
| Misspelled provenance transliteration | Use **provenance** with Russian gloss on first use |
| Mixed Latin/Russian contamination label | **загрязнение сигнала (contamination)** |
| Bare expert decision codes | Russian labels plus English UI tokens in parentheses |

### UI token policy

English menu identifiers (**Home**, **Rule Builder**, **Save expert edits**) are retained where they match the interface. Decision codes (**Accept**, **Change**, **Indeterminate**, **N/A**) are explained once per document in a table or gloss — not left unexplained in running prose.

### Asset references

- User docs now link to **PNG screenshots** under `docs/assets/screenshots/`.
- **SVG schematics** remain under `docs/assets/schematics/` and are not called screenshots.

---

## Validation

```bash
python scripts/validate_docs.py
```

Expected: pass with no mojibake, placeholder phrases, or broken relative links in reviewed files.

---

## Residual notes

- Bundled rule-pack `README_RU.md` files under `rule_packs/` were out of scope for this user-doc pass; main `docs/` tree is the release evidence set.
- In-app UI strings are governed by i18n JSON — this review covers committed markdown only.

---

## Sign-off

| Milestone | Date | Status |
|-----------|------|--------|
| RU user doc UTF-8 recovery | 2026-08-01 | Complete |
| Terminology harmonization | 2026-08-01 | Complete |
| Linked to `validate_docs.py` CI | 2026-08-01 | Complete |
