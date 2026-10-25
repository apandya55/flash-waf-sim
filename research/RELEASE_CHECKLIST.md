# FlashWAF v1.0.0 release checklist

This checklist records local release preparation. The GitHub release and Zenodo deposit have not been created.

## Verified locally

- [x] Package metadata names version `1.0.0`, Python `>=3.9`, and the declared NumPy and Matplotlib dependencies.
- [x] `CITATION.cff`, `.zenodo.json`, `pyproject.toml`, and release notes use the software title and version `1.0.0`.
- [x] The author name, repository URL, keywords, version, and MIT license match across the citation and archive metadata. `CITATION.cff` records the planned release date as 2026-10-26.
- [x] README describes only the current experiment as current evidence. It labels start-empty results as a separate historical baseline and excludes the retired buffer and durability claims from current findings.
- [x] The baseline audit and raw outputs remain in the repository for provenance.
- [x] A fresh Python 3.12.3 virtual environment installed the project with `.[dev]`; `python -m pytest -q` passed all 36 tests.
- [x] The primary 180-run experiment and 120-run sensitivity analysis regenerated with the release commands. Raw data, summaries, and both figures matched the checked-in SHA-256 hashes byte for byte.
- [x] `.zenodo.json` parses as JSON and `CITATION.cff` passes `cffconvert --validate`. The MIT license is present, package/CFF/Zenodo versions all read `1.0.0`, and the repository URL matches the configured GitHub remote.
- [x] A targeted scan found no conventional private-key blocks or common GitHub, AWS, or Google credential prefixes in project text files. This is a pattern scan, not a general security audit.
- [x] `git diff --check` passes.
- [x] Early exploratory figures moved from the top-level `figures/` folder to `research/archive/legacy_exploratory_figures/`, with a note that they are not current research evidence.
- [x] The actual LaTeX source compiles to `paper/main.pdf` with Tectonic.
- [x] Release notes state that the work has not been peer reviewed and makes no novel general scientific claim.

## Remaining before publication

- [x] Review the staged file list and release-facing diff, including archived legacy plots, metadata, results, and manuscript artifacts.
- [ ] Confirm the GitHub repository owner, release author, and permission to publish this exact tree under that account.
- [ ] After explicit authorization, enable Zenodo archiving for the repository before creating the GitHub release. Confirm that the repository is enabled in Zenodo's GitHub integration.
- [ ] Create and inspect the GitHub tag and release using the steps in `research/PUBLISHING_STEPS.md`.
- [ ] After Zenodo processes the GitHub release, inspect the resulting record, DOI, metadata, and archive contents. Follow Zenodo's correction or new-version process if any item is wrong.
- [ ] After publishing, record the DOI and update the repository badge or README citation link in a follow-up commit.

Do not publish a research preprint with this software release. No peer-reviewed publication or novel general scientific finding is claimed.
