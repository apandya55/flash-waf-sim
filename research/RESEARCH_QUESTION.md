# Research question and contribution

## Question

How do active logical-page utilization and write locality affect physical program amplification and garbage-collection work in this project's simplified greedy page-mapped FTL, under equal page-level overwrite semantics?

This is a small, reproducible sensitivity study of an educational FTL model. It does not establish a new buffering technique, commercial SSD behavior, or hardware lifetime prediction. Its defensible contribution is a corrected, explicitly bounded experimental artifact showing how measured GC costs in this simulator vary with utilization and workload locality, with raw seeded trials and executable bookkeeping checks.

## Hypotheses

1. Higher active utilization leaves fewer invalid/free-page placement choices and generally increases migration work per host program once GC is sustained.
2. A hot/cold distribution can change GC cost relative to uniform updates because invalid pages become concentrated in hot regions while cold valid pages can increase victim relocation cost.
3. These are conditional hypotheses: greedy GC and allocation interactions may reverse or flatten trends, which will be reported as observed.

## Novelty assessment

The general effects of overprovisioning, locality, and GC on write amplification are established in FTL literature. No claim of algorithmic novelty is made. This work is a reproducible computational sensitivity study and research-software correction. Before any journal submission, authors should expand the literature review and position the limited result against prior FTL analyses.

## Design

- Independent variables: active logical pages as a fraction of physical pages (40%, 70%, 85%); address distribution (uniform and hot/cold); independent PRNG seeds; fixed run length.
- Dependent variables: submitted page programs, GC page copies, total modeled page programs, block erasures, program amplification `(host programs + GC copies) / host programs`, and per-block erase-count distribution.
- Controlled variables: device geometry, page size, allocator, GC threshold, payload size, and program count per trial.
- Assumptions: one logical page is one simulator LBA; every write is a full-page replacement; no host buffer, cache, crashes, compression, parallelism, latency, or physical failure model.
- Evidence required: raw trial JSON, configuration and software versions, conservation/L2P invariants at each trial end, deterministic seed reproduction, and no-GC analytical checks in tests.

The proposed crash/buffer question is rejected for this architecture: its buffer discards record addresses, and its crash code does not implement recovery. A valid study of that question would require substantial application-log and recovery semantics outside this minimum correction.
