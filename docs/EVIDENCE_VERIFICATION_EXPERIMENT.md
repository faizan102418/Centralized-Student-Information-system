# Evidence-verification experiment

## Purpose
Compare the existing RAG pipeline (System A) with the same pipeline plus a
deterministic post-generation evidence check (System B). The checker tests
whether the answer contains the value for a recognized structured field in
the evidence retrieved for the authorized student ID.

This is a narrow, transparent intervention. It is not a general-purpose agent
reasoning evaluator, does not prove every sentence is grounded, and does not
establish that verification improves performance.

## Conditions
- System A: `answer_question(..., evidence_verification=False)` (default).
- System B: `answer_question(..., evidence_verification=True)`.
- Keep the dataset, DB snapshot, user permissions, model, prompt, embedding
  model, retrieval k=4, and Jev candidate-resolution setting identical.
- The intended difference is the post-generation evidence check.
- Supported fields: discipline, scholarship name/status, fee status, roll
  number, and registration number. Unknown fields fail closed.

## Benchmark
`data/eval/synthetic_eval.jsonl` contains 200 fictional cases: 100 answerable,
50 ambiguous, and 50 with a missing requested field. The associated synthetic
records are in `data/eval/synthetic_students.json`. To load the fixture records into a test database, first apply `data/seed.sql`, then run `mysql -u root -p project_data < data/eval/seed_synthetic_eval.sql`. These are seed cases, not
a representative sample of real student queries. Freeze the dataset before
comparison and do not tune on held-out cases.

## Prediction format
Save one JSON object per case in a predictions JSONL file:
```json
{"case_id":"ANS-001","decision":"answer","answer":"Computer Science"}
{"case_id":"AMB-001","decision":"clarify","answer":""}
{"case_id":"MIS-001","decision":"abstain","answer":""}
```
Decision must be `answer`, `clarify`, or `abstain`. Preserve raw outputs
separately; record model ID, time, latency, condition, and API errors. Never
log credentials or real student data.

## Scoring
```bash
uv sync --extra dev
uv run python scripts/evaluate_research.py --predictions experiments/results/system_a.jsonl
uv run python scripts/evaluate_research.py --predictions experiments/results/system_b.jsonl
```
Add `--output results.json` to save the metrics. The evaluator reports decision
accuracy, answer coverage, exact answer accuracy among answered cases,
correct-answer rate over all answerable cases, unnecessary non-answer rate,
unsafe-answer rate on unanswerable cases, clarification rate for ambiguous
cases, and abstention rate for missing fields. Exact matching is conservative:
manually review semantically equivalent paraphrases. Always report counts and
denominators with percentages.

## Limitations and safeguards
1. The verifier checks whether the requested field value occurs as a substring
   in the generated answer. It can miss additional unsupported claims in a
   longer answer. This is not full claim-level faithfulness.
2. A field missing from retrieved context may be a retrieval failure even if
   the source database contains it. Record retrieval failure separately from
   truly missing source data.
3. Rule-based matching may reject valid paraphrases or unusual field labels.
4. Synthetic results do not establish generalization to other institutions,
   languages, schemas, or agent architectures.
5. Keep role-based access checks enabled in both conditions. Verification
   never grants authorization.
6. Do not use real student data with third-party APIs without approval,
   consent, and suitable data-protection safeguards.
7. This PR contains no experimental results. Do not claim an improvement
   until both conditions have been run.
