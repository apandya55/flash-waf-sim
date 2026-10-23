# Research question and contribution

## Question

How do active logical-page utilization and write locality affect physical program amplification and garbage-collection work in this project's simplified greedy page-mapped FTL, under equal page-level overwrite semantics?

This is a small, reproducible sensitivity study of an educational FTL model. It does not establish a new buffering technique, commercial SSD behavior, or hardware lifetime prediction. Its defensible contribution is a corrected, explicitly bounded experimental artifact showing how measured GC costs in this simulator vary with utilization and workload locality, with raw seeded trials and executable bookkeeping checks.

## Hypotheses

1. Higher active utilization leaves fewer invalid/free-page placement choices and generally increases migration work per host program once GC is sustained.
2. A disjoint hot/cold distribution (80% of updates to 10% of active pages; 20% to the remaining addresses) can change GC cost relative to uniform updates because invalid pages become concentrated in hot regions while cold valid pages can increase victim relocation cost.
3. These are conditional hypotheses: greedy GC and allocation interactions may reverse or flatten trends, which will be reported as observed.

## Novelty assessment

The general effects of overprovisioning, locality, and GC on write amplification are established in FTL literature. The specific reversal measured here is not claimed as new: it may be useful as a reproducible characterization of this implementation, but the evidence does not support a general storage-systems contribution. No claim of algorithmic novelty is made. Before submission, the author must deepen the literature synthesis and verify the relevance and interpretation of each cited study.

## Design

- Independent variables: active logical pages as a fraction of physical pages (40%, 70%, 85%); address distribution (uniform and disjoint hot/cold); five paired seed blocks; fixed run length.
- Dependent variables: submitted page programs, GC page copies, total modeled page programs, block erasures, program amplification `(host programs + GC copies) / host programs`, and per-block erase-count distribution.
- Controlled variables: device geometry, page size, allocator, GC threshold, payload size, and program count per trial.
- Assumptions: one logical page is one simulator LBA; every write is a full-page replacement; no host buffer, cache, crashes, compression, parallelism, latency, or physical failure model.
- Evidence required: raw trial JSON, configuration and software versions, conservation/L2P invariants at each trial end, deterministic seed reproduction, and no-GC analytical checks in tests.

## Final interaction estimate

The six cells comprise 30 condition runs in five paired seed blocks, not 30 independent replications. Common random numbers align latent random draws across conditions, while address sequences differ by the intended workload transformation. The hot/cold-minus-uniform effects were +0.19936, -0.13604, and -1.78292 at 40%, 70%, and 85%; paired 95% t intervals with df=4 were [0.18603, 0.21269], [-0.15308, -0.11900], and [-1.86718, -1.69866]. Difference-in-differences relative to 40% were -0.33540 at 70% ([-0.35020, -0.32060]) and -1.98228 at 85% ([-2.05973, -1.90483]). These are descriptive estimates over five fixed simulator seed blocks, not general population or hardware inference.

The proposed crash/buffer question is rejected for this architecture: its buffer discards record addresses, and its crash code does not implement recovery. A valid study of that question would require substantial application-log and recovery semantics outside this minimum correction.
