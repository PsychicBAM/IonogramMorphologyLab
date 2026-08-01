# Release Process

1. Confirm the target version in package metadata, application `__version__`, settings defaults, installer metadata and user-facing About text.
2. Run tests, hygiene, README and version validators; record security-audit results and dependency-audit availability.
3. Review changelog, EN/RU documentation, license/third-party notices and citation metadata.
4. Build portable and installer artifacts only from a clean, reviewable source tree; smoke-test on a supported Windows environment.
5. Publish checksums and release notes, then archive the validation record. Do not claim scientific validation from release testing.
