# Evidence-verification experiment

## Purpose
Compare the existing RAG pipeline (System A) with the same pipeline plus a
deterministic post-generation evidence check (System B). The checker tests
whether the answer contains the value for a recognized structured field in
the evidence retrieved for the authorized student ID.

This is a narrow intervention, not a general-purpose fact checker. It does not
prove every sentence is grounded or establish that verification improves performance.

## Conditions
- System A: answer_question with evidence_verification=False (default).
- System B: answer_question with evidence_verification=True.
- Keep dataset, DB snapshot, user permissions, model, prompt, embedding model,
  retrieval k=4, and Jev candidate-resolution setting identical.
- The intended difference is the post-generation evidence check.
- Supported fields: discipline, scholarship name/status, fee status, roll
  number, and registration number. Unknown fields fail closed.

## Benchmark
synthetic_eval.jsonl contains 200 fictional cases: 100 answerable, 50
ambiguous, and 50 with a missing requested field. The associated synthetic
records are in data/eval/synthetic_students.json. The benchmark is frozen.

The V1 missing-field cases ask for CGPA/GPA, which the current checker does
not recognize. System B therefore tests fail-closed handling of an
unrecognized field, not successful detection that the source record lacks
CGPA. A future benchmark version should separately test recognized fields
absent from source records and retrieval failures.

Load the fixture into the isolated research database after applying data/seed.sql:
```bash
sudo mariadb research_eval < data/eval/seed_synthetic_eval.sql
```
Do not use the production/default project_data database. The seed cases are
not representative of real student queries.

## Running the experiment
The runner makes real Groq and Jev API calls. It loads the faculty1 research
identity, builds the vector store once, then runs the selected conditions
against the same in-memory store. Keep the research database limited to
fictional seed records.

Start with a balanced six-case smoke test (two cases per category):
```bash
PYTHONPATH=src uv run python scripts/run_research_experiment.py --pilot --system both
```

Run the full benchmark only after inspecting pilot outputs:
```bash
PYTHONPATH=src uv run python scripts/run_research_experiment.py --system both
```

Run one condition independently with --system A or --system B. Use --limit N
for the first N cases instead of --pilot. Use --output-dir PATH to isolate
runs. Existing output is never silently overwritten. If an API/operational
error stops a run, fix the cause and rerun with --resume; successful case IDs
are skipped. Resume validates the dataset hash and selected case IDs. The raw
error entry is retained; errors are not scored as abstentions.

## Output files
- system_a_predictions.jsonl / system_b_predictions.jsonl: evaluator input
  with case_id, decision, and answer. Common answer framing is stripped for
  exact-match scoring; inspect this derived field manually.
- system_a_raw.jsonl / system_b_raw.jsonl: untouched response text, observable
  decision, total latency, and per-call Jev telemetry.
- metadata.json: dataset SHA-256, selected case IDs, model IDs, threshold,
  embedding model, retrieval k, database name, and condition definitions.

The response classifier uses deterministic string rules for answer, clarify,
abstain, and error. It is an operational classifier, not a semantic judge.
Review raw outputs before interpreting metrics. "Not available" is counted
as abstention. Jev/API failures are errors and stop the run. Jev's numeric
value is recorded as jev_score, not as a calibrated probability.

## Scoring
After a complete run:
```bash
uv run python scripts/evaluate_research.py --predictions experiments/results/system_a_predictions.jsonl
uv run python scripts/evaluate_research.py --predictions experiments/results/system_b_predictions.jsonl
```
Add --output results.json to save metrics. The evaluator reports decision
accuracy, answer coverage, exact answer accuracy among answered cases,
correct-answer rate over all answerable cases, unnecessary non-answer rate,
unsafe-answer rate on unanswerable cases, clarification rate for ambiguous
cases, and abstention rate for missing fields. Exact matching is conservative:
manually review paraphrases. Report counts and denominators with rates. Compare
conditions on the same completed case set.

## Limitations and safeguards
1. The verifier checks whether the requested field value occurs as a substring
   in the generated answer. It can miss additional unsupported claims.
2. A field missing from retrieved context may be a retrieval failure even if
   the source database contains it.
3. Rule-based matching may reject valid paraphrases or unusual field labels.
4. Synthetic results do not establish generalization to other institutions,
   languages, schemas, or agent architectures.
5. Keep RBAC enabled in both conditions. Verification never grants authorization.
6. Do not use real student data with third-party APIs without approval, consent,
   and suitable data-protection safeguards.
7. Ambiguous cases are resolved locally before Jev and Groq calls; Jev
   telemetry will therefore be absent for those cases.
8. This PR contains no experimental results. Do not claim improvement until
   both conditions have been run.
