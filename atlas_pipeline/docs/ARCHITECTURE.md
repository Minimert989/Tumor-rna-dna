# Architecture

## Pipeline graph

```text
OncoTree ───────────────┐
                       ├─> cancer taxonomy / aliases ───────────────┐
ClinicalTrials.gov ─────┘                                           │
                                                                    ├─> DuckDB normalized atlas
Drugs@FDA ──────────────┐                                           │
openFDA label bulk ─────┼─> drug / approval / label normalization ─┤
DailyMed v2 ────────────┤                                           │
RxNorm ─────────────────┘                                           │
                                                                    │
OncoKB API/Annotator ─────> biomarker–therapy evidence ─────────────┤
                                                                    │
NCCN export ───────────────> guideline recommendation import ───────┤
eviQ export ───────────────> regimen component import ──────────────┤
Micromedex/Lexidrug export -> licensed monograph import ─────────────┘

DuckDB -> QA reports -> CSV + Parquet + Excel
```

## Completeness strategy

- The master denominator is every active OncoTree tumor type, not a hand-written list.
- ClinicalTrials.gov exhaustive mode queries every OncoTree name and also broad oncology root terms.
- Trial overlaps are deduplicated by NCT ID.
- openFDA exhaustive mode downloads every drug-label bulk partition.
- Drugs@FDA is ingested from the complete weekday data ZIP, not search results.
- Records that fail cancer mapping remain in `mapping_issues`; they are never silently dropped.
- Long-running ClinicalTrials synchronization checkpoints each completed cancer query and resumes safely.

## Licensing boundary

NCCN, Micromedex and Lexidrug are not public bulk APIs. eviQ also does not expose a general-purpose public API for complete protocol replication. The pipeline therefore accepts authorized exports and records reviewer/date/version metadata. It does not bypass authentication, copy protected content from a subscription, or claim that a public-label substitute is identical to those licensed databases.
