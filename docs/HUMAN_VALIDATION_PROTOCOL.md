# Human-validation protocol for agent answer trustworthiness

## Purpose
Human review complements automated exact-match and decision metrics. It evaluates observable answer correctness, support from retrieved evidence, and whether the system chose the appropriate answer/clarify/abstain action. Reviewers must not infer or score hidden chain-of-thought.

## Sample and workload
- Select 40 unique benchmark queries from the frozen 200-case set using a documented random seed and stratification: 20 answerable, 10 ambiguous, and 10 missing-information cases.
- Review all available outputs for those queries across all three systems and all five runs. With complete runs this is 40 x 3 x 5 = 600 outputs.
- If a run failed operationally, mark it as an operational failure; do not silently replace it with an abstention.
- Preserve query-level clustering in analysis. The 600 output records are not 600 independent queries.

## Blinding and review procedure
1. Export outputs with randomized review IDs. Hide system name, run number, and model condition from reviewers.
2. Give both reviewers the same query, expected benchmark state, and exact retrieved evidence snapshot used for that run. Do not show the expected answer before the initial independent rating if answer correctness is being judged.
3. Two reviewers independently rate every selected output.
4. Resolve disagreements by discussion or a third adjudicator; preserve both original ratings and the adjudicated label.
5. Record reviewer instructions, rubric version, sampling seed, and any exclusions before inspecting aggregate system results.

## Rating rubric

### A. Answer correctness
- correct: materially answers the requested question and matches the source record.
- partially_correct: contains a correct core value but omits a material qualification or includes a minor error.
- incorrect: wrong, unsupported, or materially misleading answer.
- not_applicable: system clarifies, abstains, or fails operationally.

### B. Evidence support (observable faithfulness)
- 2 - fully_supported: every factual claim needed to answer the query is directly supported by the supplied retrieved evidence.
- 1 - partially_supported: the central answer is supported but at least one material detail is missing or unsupported.
- 0 - unsupported: the answer conflicts with evidence or its central factual claim is not supported.
- not_applicable: no factual answer was provided.

Reviewers should split multi-claim responses into atomic factual claims in a notes field. This rubric evaluates evidence support, not whether the model's private reasoning was correct.

### C. Decision appropriateness
- appropriate_answer: answer when the required information is present and the entity is unambiguous.
- appropriate_clarification: ask for clarification when multiple candidate records match.
- appropriate_abstention: abstain when a recognized requested field is genuinely absent from the source record.
- inappropriate_action: answer, clarify, or abstain when another action is warranted.
- operational_failure: API, infrastructure, or execution error; analyze separately.

### D. Error type (multi-label)
Use one or more: wrong entity, wrong field/value, unsupported extra claim, missing evidence, over-abstention, failure to clarify, unnecessary clarification, incorrect abstention, retrieval failure, operational failure.

## Analysis
- Report counts and denominators for each label.
- Report evidence-support distribution and answer correctness among applicable answers.
- Compute Cohen's kappa for categorical labels (decision appropriateness and correctness after mapping to categorical values). For the ordinal 0-2 evidence-support scale, use a weighted Cohen's kappa and state the weighting scheme.
- Report raw agreement as well as kappa; kappa can be affected by prevalence.
- Report adjudicated results separately from pre-adjudication inter-rater agreement.
- Aggregate or resample at the query level. For comparisons, keep all repeated outputs for a sampled query together; do not treat 600 outputs as independent observations.
- Treat this 40-query sample as a focused validation exercise, not definitive population-level validation. Report uncertainty and sampling limitations.

## Required review data columns
review_id, case_id, system_blinded, run_blinded, query, retrieved_evidence, raw_output, correctness, evidence_support, decision_appropriateness, error_type, reviewer_notes, adjudicated_label.

## Privacy and safety
Use only the fictional benchmark records. Do not export real student records or send identifiable student data to third-party model providers for this experiment.
