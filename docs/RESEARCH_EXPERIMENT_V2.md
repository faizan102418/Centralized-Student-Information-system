# Research experiment v2: accuracy and trustworthiness of RAG agents

## Research objective
Evaluate observable accuracy and trustworthiness of retrieval-augmented agents answering structured database questions. The study does not inspect or claim to measure hidden chain-of-thought. It evaluates final answers, their support in retrieved evidence, and observable answer/clarify/abstain decisions.

## Benchmark version 2
The benchmark contains 200 fictional cases:
- 100 answerable cases with source values present.
- 50 ambiguous-name cases with multiple matching student records.
- 50 missing-information cases targeting the recognized fee_status field, split evenly between two source states:
  - 25 null_value cases: the student and fee-submission row exist, but fee_status is SQL NULL (SYN-021 through SYN-030).
  - 25 related_record_absent cases: the student exists, but no fee-submission row exists (SYN-011 through SYN-020).

The previous V1 missing cases asked for CGPA/GPA, a field not represented in the database schema. Those cases tested unsupported-field handling, not genuine missing-value detection. V2 replaces them with recognized-field cases that distinguish a NULL column value from an absent related record. The SQL fixture creates ten students for each missing state; the groups are disjoint.

Load the isolated database:
```bash
mysql -u root -p -e "CREATE DATABASE research_eval;"
mysql -u root -p research_eval < data/seed.sql
mysql -u root -p research_eval < data/eval/seed_synthetic_eval.sql
```
The SQL fixture is intended for a clean research_eval database. Do not load it repeatedly without resetting the fixture or checking for duplicate primary/unique keys.

Validate expected labels against the database:
```bash
DB_NAME=research_eval PYTHONPATH=src uv run python scripts/validate_research_benchmark.py
```
The validator refuses to run against a database whose configured name is not research_eval. It checks answerable values, candidate existence for ambiguous cases, SQL NULL values for null_value cases, and absent fee-submission rows for related_record_absent cases. Preserve the generated validation JSON alongside the experiment artifacts. The validator checks source-state validity; it does not prove that vector retrieval succeeds.

## Experimental conditions
All conditions share local deterministic candidate matching, ambiguity clarification, role-based authorization, database snapshot, retrieval settings, prompt/model configuration, and student-ID-scoped retrieval. Ambiguity clarification is a shared safety control and is not claimed as a treatment effect.

- System A — baseline: RAG generation without the experimental evidence verifier or pre-generation missing-evidence gate.
- System B — post-generation verification: System A plus a deterministic verifier that checks whether the answer contains the retrieved value for a recognized requested field.
- System C — pre-generation evidence gate + verification: System B plus a pre-generation gate. If the query requests a recognized field and that field is absent from retrieved evidence, System C abstains before calling the LLM. When the field is present, it proceeds to generation and post-generation verification.

Contrasts:
- A vs B: effect of adding post-generation requested-field verification.
- B vs C: incremental effect of the pre-generation evidence-availability gate.
- A vs C: combined difference between baseline and the two verification safeguards.

The verifier is deliberately narrow. It is not a general-purpose fact checker and does not validate every claim in a multi-sentence response. System C's gate tests absence from retrieved evidence, which may arise from a source-level missing record or retrieval failure. The benchmark validator separately establishes that V2 missing cases are genuinely absent in the source database. Report retrieval failures separately where diagnostics permit.

## Repeated-run design
Run five executions per query per system (200 queries x 5 repeats x 3 systems = 3,000 attempts when complete):
```bash
DB_NAME=research_eval PYTHONPATH=src uv run python scripts/run_repeated_research_experiment.py --system all --repeats 5 --output-dir experiments/repeated_abc
```
Use --disable-jev only for a separately labelled no-Jev ablation. Never pool Jev-enabled and no-Jev results. Use --resume only with exactly matching dataset, conditions, model configuration, seed, and repeat count. The runner stores raw output, decision, run number, latency, and verifier diagnostics. Operational errors remain errors and stop the run; they are not scored as abstentions.

The runner rotates condition order between runs using a recorded deterministic seed. It builds one vector store per invocation. Record the exact database fixture, model IDs, environment, and dataset hash with the output artifacts.

## Metrics
Primary query-level metrics after majority aggregation over the five runs:
- Decision accuracy for answer, clarify, and abstain actions.
- Answer coverage on answerable queries.
- Exact answer accuracy when answered, plus correct-answer rate over all answerable queries.
- Unsafe-answer rate on ambiguous and genuinely missing queries.
- Clarification precision and recall.
- Missing-information abstention precision and recall.
- Per-query decision consistency and median latency across repeats.

Report run-level distributions as descriptive variability, not independent samples. The evaluator uses query-level paired bootstrap resampling for decision-accuracy differences and retains paired outcomes across systems. Do not apply McNemar to individual repeated attempts; if used, first define a query-level binary outcome and state the aggregation rule. Correct for multiple pairwise comparisons (A-B, B-C, A-C) when making confirmatory claims. Latency is descriptive; compare paired per-query medians and avoid causal claims based on one sequential run.

Automated exact match is conservative and cannot establish semantic correctness or evidence faithfulness. Use the human-validation protocol in docs/HUMAN_VALIDATION_PROTOCOL.md.

## Human validation
Review 40 unique queries (20 answerable, 10 ambiguous, 10 missing), selected with a recorded seed. Two independent reviewers assess all five runs across A/B/C (up to 600 outputs), blinded to condition. Rate answer correctness, evidence support, and decision appropriateness using the documented rubric. Report raw agreement and Cohen's kappa for categorical labels; use weighted Cohen's kappa for ordinal evidence support. Adjudicate disagreements and report the adjudicated dataset. This is an exploratory validation sample, not definitive generalization evidence.

## Interpretation limits
- Synthetic records do not establish generalization to real institutions, other schemas, languages, or agent architectures.
- A deterministic field/value check can miss unsupported claims elsewhere in an answer.
- Evidence absence at retrieval time is not automatically proof of source-level absence; use the frozen DB validation.
- The shared name clarification and RBAC safeguards are held constant across conditions.
- Do not describe hidden reasoning as measured. The measured objects are observable outputs, evidence alignment, and decisions.
- Do not report improvements until the benchmark validation succeeds and all required runs and human review are complete.
