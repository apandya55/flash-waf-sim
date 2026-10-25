# Submission-readiness assessment

Updated October 26, 2026 after the bounded validation sprint. This report is not a submission. No paper or data have been sent to a journal.

## Research redesign update, October 25, 2026

The experimental protocol and manuscript changed after the venue screen above. The original start-empty five-seed dataset is preserved under `research/results/baseline_start_empty_5seed/`. The revised experiment prepopulates every active LBA, performs 5,000 warm-up updates, measures the next 5,000 updates, and verifies equal mapped and valid page counts at both phase boundaries. It includes 30 paired seed blocks across six conditions, or 180 condition runs. The previous sign reversal did not recur: the measured hot/cold-minus-uniform contrasts are +0.32987 [0.32665, 0.33310], +0.60656 [0.60054, 0.61258], and +0.80465 [0.78676, 0.82253] at 40%, 70%, and 85% occupancy, with paired descriptive Student-t intervals at df=29. The revised manuscript and figure report these results.

This change resolves the baseline's unequal realized occupancy and mixed startup/measurement concerns for the reported design. It does not establish steady-state convergence, isolate the causal contribution of prepopulation versus warm-up versus longer seeding, or validate against a physical device. The completed sensitivity grid and qualitative analytical comparison are documented below and in `research/VALIDATION.md`; they do not alter the NO-GO manuscript decision. For software archiving, identify the project as a simulator, preserve the baseline separately, and include the reproduction environment and raw results.

## Current decision

**NO-GO for pursuing a research manuscript on the current results.** The revised experiment is reproducible and its software behavior is documented, but the evidence supports only an implementation-specific characterization. The baseline sign reversal disappeared after the protocol redesign. The separate sensitivity grid retains a positive hot/cold-minus-uniform effect in tested workload, geometry, and warm-up variants, while its magnitude changes. The study does not demonstrate a novel general relationship, numerical validation against an analytical model, hardware relevance, or a result likely to justify a standalone research paper.

**GO for preparing a software release and Zenodo software archive**, clearly labeled as an educational/research simulator and reproducible experimental artifact. Keep the manuscript as technical documentation or a software-artifact note unless new evidence establishes a distinct contribution. Before tagging or archiving, complete `research/RELEASE_CHECKLIST.md`; no external release has been made.

The analytical comparison with Agarwal and Marrow (2010) is directional only. Uniform-workload amplification increases with occupancy in the simulator, consistent with their over-provisioning analysis. The assumptions differ, so this does not validate the simulator numerically. Literature already covers write amplification, greedy GC, hot/cold data, and locality-aware FTL/GC. The bounded sprint does not establish novelty.

## Historical venue screen

The following venue notes were collected October 23, 2026, before the revised primary experiment and bounded sprint. They are not a recommendation to submit the current manuscript.

PennScience High School Journal has a stated November 1, 2026, 11:59 p.m. Eastern deadline. The current scientific NO-GO supersedes the earlier timing assessment: do not rush a research submission to meet this deadline. The earlier open questions about eligibility, format, citations, and AI policy would also remain.

JEI remains a poor scope match for this computational simulator study, and its published AI-use restrictions described below would need direct review against the complete research workflow. Do not submit the manuscript to JEI.

## Prior assessment, retained for context

PennScience High School Journal is the closest fit and has a stated November 1, 2026, 11:59 p.m. Eastern deadline. The calendar leaves nine days, but submission by that date is **not currently responsible**: author eligibility and authorship need confirmation, the manuscript is not in the journal's required format, the current author-facing materials conflict on the page limit and citation presentation, no public AI policy was located, and the author has not yet completed a line-by-line verification of the revised manuscript, sources, and results. A rushed submission would risk avoidable compliance and accuracy problems. The deadline is achievable only if those items are promptly resolved and the student author completes that review; the present report does not certify that they can be.

JEI is not recommended for this project as conducted. Its published scope excludes computer-science research and manuscripts that only introduce or compare a model or method. Its current AI policy also disallows several uses that occurred in this research workflow, including reading/summarizing published studies, statistical analysis/calculations, data mining, and writing/revising text beyond minor proofreading after human drafting. A disclosure would not make those uses compliant. The project should not be submitted to JEI under the current policy. The public JEI guidance also requires an adult senior author who submits, use of its Word template, and a $49 submission fee (with a waiver request pathway).

No other student journal has been verified here as a better immediate target under current scope, eligibility, fee, peer-review, and AI-use requirements. If PennScience cannot resolve the open questions or the deadline is missed, pause and screen other student journals individually rather than treating the venue shortlist as an endorsement.

## Historical baseline findings

The following results belong only to the archived start-empty five-seed baseline. They are retained for provenance and must not be presented as the revised study's finding. In that baseline, the paired hot/cold-minus-uniform program-amplification contrast was positive at 40% and negative at 70% and 85%, for one disjoint synthetic hot/cold construction, one geometry, and one run length. The revised prepopulated protocol and the bounded sensitivity grid did not reproduce this reversal.

The baseline raw dataset has five independent pseudorandom seed blocks. Each block contains all six conditions; common random numbers pair latent draws by seed, while condition transformations intentionally produce different address sequences. The corrected hot and cold ranges are disjoint. Its paired locality effects (hot/cold minus uniform) and descriptive paired 95% Student-t intervals with df=4 are:

| Active utilization | Mean paired contrast | 95% descriptive interval |
|---|---:|---:|
| 40% | +0.19936 | [0.18603, 0.21269] |
| 70% | -0.13604 | [-0.15308, -0.11900] |
| 85% | -1.78292 | [-1.86718, -1.69866] |

Difference-in-differences relative to 40% are -0.33540 at 70% ([-0.35020, -0.32060]) and -1.98228 at 85% ([-2.05973, -1.90483]). These intervals describe variation among five fixed simulation seed blocks only. They are not evidence about device/workload populations or hardware. The 30 rows must not be described as 30 independent replications of the interaction.

The methodological repair was to prepopulate active addresses, separate warm-up from measurement, compare equal mapped-page occupancy, and increase the primary paired seed count to 30. The bounded sensitivity sprint then varied workload family, geometry, and warm-up length with ten paired seed blocks per cell. These changes make the revised result interpretable, but they do not identify which individual protocol change removed the baseline reversal.

## PennScience requirements and blockers

Official pages checked October 23, 2026:

- [Guidelines](https://pshsj.org/guidelines)
- [FAQ](https://pshsj.org/faq)
- [Submissions](https://pshsj.org/submissions)
- [Style guide PDF](https://cdn.prod.website-files.com/66a0feaeb9ff476a6a15d235/66b194525f7d7e2a2445ff33_Style%20Guide.pdf)
- [Manuscript template DOCX](https://cdn.prod.website-files.com/66a0feaeb9ff476a6a15d235/66b194a44e75df9012412355_Manuscript%20Template.docx)
- [Publication permission form PDF](https://cdn.prod.website-files.com/66a0feaeb9ff476a6a15d235/66b25f942622f339303ed3cb_Permission%20Form.pdf)

The site says the annual deadline is November 1 at 11:59 p.m. EST; the FAQ says the journal reviews original work in social/natural sciences and engineering, all listed authors must be in high school or have completed the research while in high school, manuscripts are 3–5 pages including references and figures, and references must be APA 7. It says review results arrive together by mid-February. Submission requires three files: the manuscript (with figures), a separate PPTX containing figures, and the Publication Permission Form. The primary author submits. The public pages reviewed do not state a submission fee. The homepage search result still labels the open call “2025-2026”; the submission page states the annual November 1 close. Confirm that the 2026 call is active in the form before preparing a final package.

The downloaded template describes 3–5 pages excluding references, while the FAQ says including references. The template demonstrates numbered in-text citations, while the FAQ says APA 7. The manuscript currently uses a single-column 11-point LaTeX article layout and numbered bibliography style; it is not formatted to the template's Times New Roman 10-point body, 9-point abstract, double columns, 0.75-inch margins, 0.95 line spacing, and requested reference style. Resolve the conflicting page-limit and citation instructions with the editors before final layout.

No PennScience AI-use policy was found in its current public Guidelines, FAQ, or Submissions pages or linked template/style materials. This is **unverified**, not permission to use AI. The author should ask the journal whether its policy permits AI assistance with research auditing, code/experiment changes, statistical analysis, literature discovery, and manuscript editing, and how to disclose it. Revise the disclosure only after receiving the actual requirement; do not imply journal approval.

Remaining PennScience blockers / author actions:

1. Confirm that the primary author and every listed author meet the high-school eligibility rule, confirm contribution order, and ensure non-high-school contributors are handled as the journal directs.
2. Confirm that the 2026 submission call is open and ask the editors to resolve the page-count and citation-style inconsistency.
3. Obtain the current AI policy in writing or from an official published source; determine whether this AI-assisted workflow is eligible and what disclosure is required.
4. Have the student author verify every reference against the original publication, each reported number against `research/results/summary.json`, the raw trial JSON, and the source; review all claims and approve the final text.
5. Reformat into the current PennScience template/style after editorial answers. The present LaTeX source is not compliant with that template.
6. Prepare the separate figures PPTX and complete the permission form with required author/mentor acknowledgements and signatures. These are not included because author identities, permissions, and signatures cannot be supplied by this audit.
7. Check the submission form and all rules again immediately before the deadline.

## JEI scope and policy screen

Official pages checked October 23, 2026:

- [Submission guidelines](https://emerginginvestigators.org/submissions/guidelines)
- [Topics accepted / hypothesis-driven research](https://emerginginvestigators.org/submissions/hypothesis-driven-research)
- [Academic honesty and AI](https://emerginginvestigators.org/submissions/academic-honesty-and-ai)
- [Author eligibility](https://emerginginvestigators.org/submissions/author-eligibility)
- [Manuscript content](https://emerginginvestigators.org/submissions/manuscript-content)
- [FAQ](https://emerginginvestigators.org/submissions/faq)

JEI says its scope is natural-science manuscripts where student authors develop and clearly test a hypothesis; it lists computer science, statistics, mathematical modeling without supporting experiments, and work that only introduces/optimizes/compares a model, method, or algorithm among excluded topics/types. This manuscript is a computational simulator sensitivity study, so it is a poor scope match. JEI requires a student and adult senior author, adult submission in its manuscript template, and charges $49 at submission (waivers may be requested).

JEI's AI page says it cannot publish manuscripts using AI to read/summarize/analyze published studies, write or revise text except minor proofreading after human drafting, create images, conduct statistical analysis/modeling/calculations, data mine, or cite/create reference lists. This workflow included multiple listed uses. Therefore JEI is blocked under the published policy unless JEI itself changes or formally clarifies that policy; changing the disclosure alone is insufficient. Do not submit this manuscript to JEI as currently produced.

## Literature screened

The manuscript cites ten published studies. DOI records were checked against Crossref metadata for nine; Agrawal et al. is linked to the USENIX paper. The papers span write-amplification analyses and models, greedy garbage collection and valid-page distributions, and hot/cold or locality-aware collection/FTL policies. These sources establish that locality and GC behavior are mature topics. The current paper's possible contribution is the reproducible, bounded characterization and correction of its own simulator experiment, not a novelty claim about the general utilization-locality interaction. The author still needs to read and synthesize the papers directly before journal submission.

## Actual manuscript build and local files

`paper/main.tex` and `paper/references.bib` are the source manuscript. `paper/main.pdf` must be the actual output of the LaTeX build, not a separately typeset recreation. The source uses `paper/main.tex`; the compiled PDF is a research artifact but not a PennScience-formatted submission. No submission, publication, preprint deposit, or external upload has been made.
