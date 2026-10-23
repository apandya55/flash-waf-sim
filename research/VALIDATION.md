# Validation record

## Internal correctness

Baseline: 32 existing tests passed (`python3 -m pytest -q`, Python 3.12.3, pytest 9.1.1). After repair: 35 passed in 0.18 s. New tests perform repeated overwrites through repeated GC, verify latest data, check page-state conservation and erase counter totals after every write, and confirm that a full device with no invalid page raises `FlashOutOfSpaceError` without losing prior mappings. The experiment invokes the simulator invariant checker after each trial. This is software bookkeeping validation, not a NAND conformance test.

## Independent analytical checks

For a no-GC append-only workload of N full pages, the model must perform N host programs, zero GC copies, zero erasures, and program amplification 1. This follows directly from one full logical page per host program. Legacy buffered ratios were independently recomputed from displayed counters and byte sizes, but are not used as evidence because the two paths lose semantic equivalence. The new experiment has a fixed 5,000 host programs per trial; raw results verify the count and the total is exactly host programs plus GC copy programs.

## Paired design and statistical analysis

The raw data contain 30 condition runs: six utilization-by-locality cells for each of five seed blocks (11, 23, 47, 89, 101). They are not 30 independent interaction replications. The experiment now uses common random numbers: latent uniform draws are aligned by seed across conditions, although each condition maps them to a different address sequence. The hot range and cold range are disjoint. Independent pseudorandom streams provide five seed-level blocks; workload contrasts are paired within each block.

For each utilization, hot/cold-minus-uniform mean amplification differences were +0.19936 at 40% (95% paired t interval [0.18603, 0.21269]), -0.13604 at 70% ([-0.15308, -0.11900]), and -1.78292 at 85% ([-1.86718, -1.69866]). Difference-in-differences relative to 40% were -0.33540 at 70% ([-0.35020, -0.32060]) and -1.98228 at 85% ([-2.05973, -1.90483]). Each interval has df=4 and describes only the five paired simulator seed blocks. We do not use these intervals as inferential claims about physical devices or real workload populations, and do not frame the result as evidence of general statistical significance.

The paired comparison is internally consistent in seed identity and latent draw alignment after the experiment correction. It is not a matched identical address trace: the intended treatment is a change in address distribution, so condition-specific address sequences differ by design. The corrected disjoint hot/cold populations also mean the final experiment is not numerically interchangeable with the earlier overlapping hot-biased mixture.

## Literature comparison and limits

At least nine published studies reviewed in the manuscript cover measured/modelled WAF, greedy GC, valid-page distributions, hot/cold data, locality-aware FTLs, and GC policies. This literature establishes the broader locality/GC interaction as known. It does not validate our numeric reversal, nor has this audit established that the exact pattern in this exact simulator was previously published. The appropriate claim is therefore a simulator-specific reproducible characterization, not a novelty claim. No numerical comparison to hardware or published device measurements is made. DOI metadata and publisher records were checked for reference identity; the author still needs to verify each work's content and accurately represent it in the final literature synthesis.

## Unresolved limitations

No persistent FTL metadata or crash recovery; no record-level buffered equivalence; no NAND timing, channel parallelism, bad blocks, ECC, wear-out, data retention, or controller firmware; five seed blocks and one run length; startup is mixed with GC operation. `generate_figures.py` remains a legacy exploration tool. The paper figure is generated from sensitivity trial JSON by `experiments/summarize_results.py`.

## Manuscript build status

The authoritative manuscript is `paper/main.tex` with `paper/references.bib`; the actual PDF must be compiled from this source. Final seed-paired results and literature positioning have been incorporated. Venue-specific formatting and author review remain separate from scientific validation.
