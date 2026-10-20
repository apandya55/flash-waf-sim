# Zenodo and Google Scholar plan

Checked 2026-10-23 against [Zenodo GitHub integration](https://zenodo.org/account/settings/github/), [Zenodo documentation](https://help.zenodo.org/), and [Google Scholar inclusion guidance](https://scholar.google.com/intl/en/scholar/inclusion.html). Zenodo is a repository operated by CERN; a Zenodo DOI records an artifact and does not certify peer review. Google Scholar discovery is not guaranteed by a DOI.

## Recommended artifact sequence

1. Finish the code, tests, raw data, method, and paper; remove unsupported legacy findings from the README.
2. Create a versioned GitHub release for the software snapshot. Enable the Zenodo GitHub integration for this repository, then archive the release. Zenodo creates a version DOI and a concept DOI that can point to all versions. Review metadata before publishing.
3. Archive the dataset and computational paper as separate records only if the target journal permits public preprints/data release. Link records with related identifiers and cite the software version DOI in the paper. Avoid duplicate records if the GitHub release already contains the small raw dataset; use a distinct dataset record when it has independent value or needs separate citation.
4. If a journal accepts the manuscript, update links/metadata with the final published DOI. Do not upload publisher-formatted accepted files unless the journal permits it.

Suggested metadata: descriptive title; version; authors in correct order; ORCID if available; abstract; publication date; keywords (NAND flash, FTL, garbage collection, simulation, reproducibility); language; license matching repository; software/data/resource type; funding only if real; related identifiers for GitHub, paper, and dataset; and a README describing environment and reproduction commands. Do not claim institutional affiliation, peer review, hardware validation, or a publication venue that has not actually occurred.

Reserve a DOI only when a journal or manuscript needs a stable citation before publication and the reservation is allowed by that workflow. A reserved DOI is not a published record; it becomes resolvable after deposition. Keep release versions immutable; make corrections in a new version and cite the concept DOI when referring to the continuing project.

## Google Scholar discoverability

Scholar relies on crawlable scholarly documents and compliant metadata, not merely a repository DOI. Publish an accessible PDF with a clear title, author, date, abstract, references, and machine-readable metadata; keep the page crawlable and avoid login barriers. Check the official inclusion guidance for current technical requirements. Indexing can be delayed or absent and is never promised. A Zenodo preprint or software record is not an accepted journal article.

## Human-action checklist

- [ ] Select and confirm the venue's current preprint, data, AI disclosure, and fee rules.
- [ ] Review author order, contact details, license, and all public metadata.
- [ ] Create/approve the GitHub release and Zenodo record under the author's account.
- [ ] Publish the dataset/paper records only when allowed; link DOIs and repository versions.
- [ ] Submit to the journal yourself and retain the decision/review history.
- [ ] After acceptance, update related identifiers and permitted manuscript version.
- [ ] Check Google Scholar later; report indexing only if actually visible there.
