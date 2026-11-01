# Evaluating evidence verification and selective decisions in structured RAG agents

## Research objective

Evaluate observable accuracy and trustworthiness outcomes of a retrieval-augmented agent answering structured student-record questions. The study evaluates final answers, retrieved evidence, entity-resolution outcomes, and answer/clarify/abstain decisions. It does not inspect or score hidden chain-of-thought.

## Experimental conditions

All conditions use the same synthetic database snapshot, candidate matcher, authorization checks, RAG prompt, model configuration, embedding model, and retrieval settings.

- **System A — Baseline RAG:** entity matching, RBAC, scoped retrieval, and LLM answer generation. No experimental post-generation evidence verifier.
- **System B — Evidence verification:** System A plus a deterministic post-generation verifier. It checks whether the generated answer contains the value for the requested recognized field in retrieved evidence. This is a narrow structured-field check, not a general-purpose fact checker.
- **System C — Evidence verification + source-aware selective decisions:** System B plus a pre-generation source-state gate. For a recognized field, it checks whether a non-empty source value or related source record exists. It abstains when the value is genuinely NULL/empty or the related record is absent. The gate returns availability metadata only; it does not return the field value or replace RAG generation.

Name-ambiguity clarification and RBAC are shared by A/B/C. Clarification is therefore a controlled common behaviour, not an incremental contribution of System C. The planned contrasts are A-B (post-generation evidence verification), B-C (source-aware selective decision gate), and A-C (combined intervention).

## Benchmark and source validation

The data/eval/synthetic_eval.jsonl benchmark contains 200 fictional cases:

- 100 answerable;
- 50 ambiguous entity queries;
- 50 source-missing queries.

The 50 missing cases now use recognized fields and explicit source states:
- five synthetic students have discipline = NULL;
- five synthetic students have no related student_scholarship row, so scholarship_name is absent.

The corresponding synthetic SQL fixture adds those ten students and deliberately omits the five scholarship rows. The fixture deletes/replaces only SYN-* records when re-run; demo UUID records remain untouched.

**Do not interpret the benchmark as validated until the database validation script reports zero invalid cases.** Use a fresh, isolated database and never use the production/default project database.

~~~bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS research_eval;"
mysql research_eval < data/seed.sql
mysql research_eval < data/eval/seed_synthetic_eval.sql
~~~

Set DB_NAME=research_eval in the local environment, then run:

~~~bash
PYTHONPATH=src uv run python scripts/validate_research_benchmark.py
~~~

The validator checks answerable expected values against the database, verifies that each ambiguous case has multiple expected candidates in the directory, and confirms the source state for every missing case. It writes experiments/benchmark_validation.json. Preserve the SQL fixture, schema version, dataset SHA-256, and validation report with experimental outputs.

## Repeated experiment execution

The runner defaults to five repeated executions per query and supports A, B, C, both (A/B), or all (A/B/C). It makes real Groq and, unless disabled, Jev API calls.

Start with a six-case smoke test, one run per system:

~~~bash
PYTHONPATH=src uv run python scripts/run_research_experiment.py --pilot --system all --repeats 1 --output-dir experiments/pilot_abc
~~~

Inspect raw output, decisions, diagnostics, and errors before proceeding. Then run the full benchmark:

~~~bash
PYTHONPATH=src uv run python scripts/run_research_experiment.py --system all --repeats 5 --output-dir experiments/results/abc_5runs
~~~

Each run produces separate files such as:
- system_a_run_01_predictions.jsonl and system_a_run_01_raw.jsonl;
- system_b_run_01_predictions.jsonl and system_b_run_01_raw.jsonl;
- system_c_run_01_predictions.jsonl and system_c_run_01_raw.jsonl.

System B/C diagnostics are saved separately by condition. Raw logs preserve the response, observable decision, latency, error information, and Jev telemetry. Resume uses each case/run pair and checks the dataset hash, selected cases, repeat count, and Jev configuration. Do not mix Jev-enabled and no-Jev runs.

For a no-Jev ablation, use a separate output directory and label it explicitly:

~~~bash
PYTHONPATH=src uv run python scripts/run_research_experiment.py --system all --repeats 5 --disable-jev --output-dir experiments/results/abc_5runs_no_jev
~~~

This is not a replication of the Jev-enabled experiment and must not be pooled with it.

## Evaluation and statistical analysis

Aggregate repeated runs for a single condition:

~~~bash
PYTHONPATH=src uv run python scripts/evaluate_research.py \
  --predictions experiments/results/abc_5runs/system_a_run_*_predictions.jsonl \
  --output experiments/results/abc_5runs/system_a_metrics.json
~~~

Repeat for B and C. The evaluator reports per-run counts and metrics plus means and standard deviations across runs. It includes:
- decision accuracy;
- answer coverage on answerable queries;
- exact answer accuracy among answered cases;
- correct-answer rate over all answerable cases;
- unnecessary non-answer rate;
- clarification precision and recall;
- missing-information abstention precision and recall;
- median latency.

Exact matching is conservative; manually adjudicate semantic paraphrases. The evaluator does not automatically score evidence faithfulness.

For paired system comparisons:

~~~bash
PYTHONPATH=src uv run python scripts/analyze_repeated_experiment.py \
  --results-dir experiments/results/abc_5runs \
  --bootstrap-samples 10000
~~~

This computes paired, category-stratified bootstrap confidence intervals for A-B, B-C, and A-C. It averages repeated attempts within each query before resampling. The inferential unit is the query/case ID, not each repeated attempt. Report the number of queries and attempts separately. Positive latency difference means the right-hand system is slower.

## Human validation

Follow the human-validation protocol in HUMAN_VALIDATION_PROTOCOL.md and use data/eval/human_review_template.csv. The planned review selects 40 unique queries (20 answerable, 10 ambiguous, 10 missing) and reviews all five runs across all three systems (up to 600 outputs). Two reviewers independently annotate action appropriateness, answer correctness, evidence support, evidence sufficiency, and unsupported claims. Report Cohen's kappa and raw agreement. This is exploratory validation; it is not a substitute for a larger study.

## Important interpretation rules

1. A field absent from retrieved context is not necessarily absent from the source database. Check source state separately.
2. A missing related record, a NULL/empty field, an unsupported schema field, and a retrieval failure are distinct labels.
3. System C's source-state gate checks availability only; it does not itself establish that a generated answer is supported.
4. A/B/C share candidate matching and ambiguity clarification. Do not attribute clarification differences to the C-specific gate.
5. Keep RBAC enabled in every condition. Authorization is a constant safety safeguard, not an experimental intervention.
6. A deterministic substring check can miss unsupported additional claims and valid paraphrases. Human validation is needed.
7. API and infrastructure failures are operational errors, not abstentions.
8. Synthetic results do not establish generalization to real institutions, other schemas, languages, or general-purpose autonomous agents.
9. No performance improvement is claimed by this repository change. Results must be generated and interpreted after benchmark validation.
10. Use only fictional data. Do not send real student records to third-party model APIs without institutional authorization and suitable privacy safeguards.
