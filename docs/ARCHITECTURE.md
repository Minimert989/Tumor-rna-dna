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

## Core tables

- `cancer_types`: complete OncoTree hierarchy and aliases
- `drug_products`: FDA products and normalized RxNorm identities
- `drug_approvals`: applications, submissions, actions and supplements
- `drug_labels`: public label sections plus raw source identifiers
- `clinical_trials`: normalized fields plus source JSON
- `biomarker_therapy_evidence`: alteration–drug evidence
- `guideline_recommendations`: authorized guideline imports
- `regimen_components`: protocol drugs, doses, routes and schedules
- `licensed_monographs`: authorized institutional exports
- `mapping_issues`: unresolved cancer, drug and biomarker mappings
- `source_runs`: source version, timestamps, checksum and record counts

## Completeness strategy

- The denominator is every active OncoTree tumor type, not a hand-written disease list.
- ClinicalTrials.gov exhaustive mode queries OncoTree names and broad oncology roots.
- Overlapping studies are deduplicated by NCT ID.
- openFDA exhaustive mode downloads all drug-label bulk partitions.
- Drugs@FDA uses the complete data ZIP rather than search-result pages.
- Failed mappings remain in `mapping_issues`; they are never silently discarded.
- Long-running sources checkpoint progress and can resume.

## Evidence layers

```text
FDA-approved / label-defined
Guideline-recommended
Biomarker-directed evidence
Registered clinical trial
Published clinical result
Preclinical evidence
```

These layers are not collapsed into a single boolean field. A registered trial is not treated as evidence of benefit.

## Licensing boundary

NCCN, Micromedex and Lexidrug are not public bulk APIs. eviQ does not expose a general-purpose public API intended for complete protocol replication. The pipeline accepts authorized exports with reviewer, date and version metadata. It does not bypass authentication or claim that public FDA labeling is identical to licensed monographs.
