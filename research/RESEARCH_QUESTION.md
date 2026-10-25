# Research question and contribution

## Question

How do mapped logical-page occupancy and update locality affect measured program amplification and garbage-collection work in this project's simplified greedy page-mapped FTL under full-page overwrite semantics?

This is a reproducible sensitivity study of an educational FTL model. It does not establish a buffering technique, commercial SSD behavior, or hardware lifetime prediction. Its contribution is an explicitly bounded experimental artifact with raw seeded trials and executable bookkeeping checks.

## Hypotheses

1. Higher active utilization leaves fewer placement choices and can increase migration work per host program when garbage collection runs.
2. A disjoint hot/cold distribution, with 80% of updates sent to 10% of active pages, can change GC cost relative to uniform updates because update concentration changes invalid-page placement and victim relocation.
3. Greedy collection and allocation interactions can reverse or flatten these trends, so the experiment reports observed results without tuning the method to a hypothesis.

## Novelty assessment

The general effects of overprovisioning, locality, and GC on write amplification are established in FTL literature. The earlier start-empty sign reversal did not recur under the revised prepopulation and warm-up protocol. No novelty claim is made for this change or for a general locality-utilization interaction. The revised result characterizes this implementation under a specified synthetic workload. Before journal submission, the author should deepen the literature synthesis and verify each cited study's relevance and interpretation.

## Design

- Conditions: mapped active logical pages at 40%, 70%, and 85% of physical capacity, with uniform or disjoint hot/cold address distributions.
- Replication: 30 seed blocks, each covering all six conditions, using common random numbers to pair latent draws.
- Initialization: prepopulate all active addresses in ascending order, then run 5,000 warm-up updates and 5,000 measured updates.
- Outcomes: measured host page programs, GC page copies, total modeled page programs, block erasures, program amplification `(host programs + GC copies) / host programs`, and per-block erase-count distribution.
- Controlled variables: geometry, initial address layout, allocator, GC threshold, page size, warm-up length, measurement length, and full-page write semantics.
- Assumptions: one logical page maps to one simulator LBA. No host buffer, cache, crash recovery, compression, parallelism, timing, or physical failure model is included.

## Revised interaction estimate

The 180 condition runs form 30 paired seed blocks, not 180 independent replications. After prepopulation and a 5,000-update warm-up, measured hot/cold-minus-uniform effects were +0.32987, +0.60656, and +0.80465 at 40%, 70%, and 85%. Paired 95% Student-t intervals with df=29 were [0.32665, 0.33310], [0.60054, 0.61258], and [0.78676, 0.82253]. Difference-in-differences relative to 40% were +0.27669 at 70% ([0.27049, 0.28289]) and +0.47477 at 85% ([0.45711, 0.49244]). These intervals summarize seed-stream variation for this fixed model and workload generator, not hardware or workload populations. The prior five-seed start-empty study remains in its baseline archive and is not pooled with these results.

The crash/buffer question remains outside this architecture's evidence. Its buffer discards record addresses, and its crash code does not implement recovery.
