# Validation record

## Internal correctness

Baseline: 32 existing tests passed (`python3 -m pytest -q`, Python 3.12.3, pytest 9.1.1). After repair: 35 passed in 0.18 s. New tests perform repeated overwrites through repeated GC, verify latest data, check page-state conservation and erase counter totals after every write, and confirm that a full device with no invalid page raises `FlashOutOfSpaceError` without losing prior mappings. The experiment invokes the simulator invariant checker after each trial. This is software bookkeeping validation, not a NAND conformance test.

## Independent analytical checks

For a no-GC append-only workload of N full pages, the model must perform N host programs, zero GC copies, zero erasures, and program amplification 1. This follows directly from one full logical page per host program. Legacy buffered ratios were independently recomputed from displayed counters and byte sizes, but are not used as evidence because the two paths lose semantic equivalence. The new experiment has a fixed 5,000 host programs per trial; raw results verify the count and the total is exactly host programs plus GC copy programs.

## Literature comparison and limits

Published FTL work treats mapping, garbage collection, workload locality, and write amplification as interdependent. Our qualitative utilization sensitivity is compatible with the basic role of overprovisioned free space and victim relocation, but hot/cold trends differ by utilization and may reflect this simulator's greedy policy. We make no numerical comparison to hardware or published device measurements. Source citations and venue information require final author review before submission; the linked DOI records identify the works but do not validate this simulator.

## Unresolved limitations

No persistent FTL metadata or crash recovery; no record-level buffered equivalence; no NAND timing, channel parallelism, bad blocks, ECC, wear-out, data retention, or controller firmware; no confidence intervals beyond descriptive across-seed SD; five seeds and one run length; startup is mixed with GC operation. `generate_figures.py` did not finish during the baseline audit and remains a legacy exploration tool. The new figure is generated from sensitivity trial JSON by `experiments/summarize_results.py`.

## Manuscript build status

No LaTeX engine (`pdflatex`, `xelatex`, `lualatex`, `tectonic`, or `latexmk`) is installed in the environment. `paper/main.tex` and its bibliography are the authoritative manuscript sources. `paper/main.pdf` was generated as a PDF layout proof with ReportLab from the same verified results, not compiled from the LaTeX; it is therefore not a final LaTeX build. The bibliography was cross-checked for the Hu et al. DOI through Crossref; remaining venue/format adaptations and author verification are required.
