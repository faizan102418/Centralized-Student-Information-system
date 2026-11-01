# Human-validation protocol for answer accuracy and evidence support

## Purpose and scope

This protocol defines a small, stratified human review of the outputs from Systems A, B, and C. It is designed to validate answer correctness, evidence support, and the appropriateness of the observable answer/clarify/abstain action. It does **not** ask reviewers to infer or score hidden model chain-of-thought. The protocol is a planned evaluation procedure; no human-review results are claimed by this document.

## Sampling

Select 40 unique benchmark queries from the frozen, database-validated 200-case benchmark:

- 20 answerable queries;
- 10 ambiguous-entity queries;
- 10 source-missing queries.

Use a fixed random seed and retain the selected case IDs in the study log. The sample is stratified by the three task categories. It is not a population-representative sample; results should be described as exploratory human validation.

Review all available repeated outputs for each selected query:
40 queries × 3 systems × 5 runs = 600 system outputs. If a run failed operationally, retain the failure record and report it separately; do not replace it with an abstention or silently drop it.

## Reviewers and blinding

Two reviewers independently annotate each output. Hide system labels and run order during annotation where practical. Give both reviewers the same query, gold source-state record, retrieved evidence, and system response. Do not show expected system condition or automated metric scores before independent annotation.

A third adjudicator resolves disagreements after the independent pass. Preserve both original annotations and the adjudicated label. Calculate Cohen's kappa on the two independent reviewers' categorical labels before adjudication. Report raw agreement as well because kappa can be affected by class prevalence.

## Annotation unit and fields

The primary unit is one generated system output for one query and one run. If the answer contains multiple factual claims, additionally annotate each material claim in a claim-level worksheet.

Required output-level labels:

1. **Action appropriateness**
   - appropriate_answer
   - appropriate_clarification
   - appropriate_abstention
   - inappropriate_action

2. **Answer correctness** (answer outputs only)
   - correct
   - partially_correct
   - incorrect
   - not_applicable

3. **Evidence support** (answer outputs only)
   - fully_supported: every material factual claim is entailed by the supplied retrieved evidence
   - partially_supported: at least one material claim is supported and at least one is unsupported or not evidenced
   - unsupported: no material claim is supported by the supplied evidence
   - not_applicable: no factual answer was provided

4. **Evidence sufficiency**
   - sufficient
   - insufficient
   - conflicting
   - not_applicable

5. **Unsupported-claim flag**
   - yes
   - no
   - not_applicable

6. **Reviewer note**
   - Short explanation identifying the relevant evidence span or missing/conflicting fact. Do not write private chain-of-thought.

## Decision rubric

- For an answerable query, an answer is appropriate only if it answers the requested field accurately and the factual content is supported by the source record. A correct guess without evidence is not fully trustworthy.
- For an ambiguous query, clarification is appropriate when multiple candidate entities match and the system does not have enough information to select one safely. An answer choosing one candidate without disambiguation is inappropriate.
- For a source-missing query, abstention is appropriate when the requested recognized field is NULL/empty or the related record is absent in the validated source snapshot. A clarification is not a substitute for abstention when the entity is already uniquely identified.
- If the database contains the value but the retrieved evidence omits it, annotate this as a retrieval/evidence failure—not as source-level missing information.
- If a field is outside the supported schema, annotate it as unsupported-field handling; do not count it as a true missing-value detection.
- Authorization failures and API/operational failures are safety/operations outcomes and must be reported separately from answer/clarify/abstain performance.

## Analysis

Report the number of reviewed outputs and denominators for every label. Calculate:

- output-level action appropriateness rate;
- answer correctness among answer outputs and across all answerable queries;
- full evidence-support rate among answer outputs;
- partial/unsupported evidence rates;
- unsupported-claim rate;
- Cohen's kappa for action appropriateness, answer correctness, and evidence support where the category is applicable;
- raw percentage agreement for each label.

For claim-level evidence annotation, report the number of claims and support labels. Do not treat claims or repeated outputs as independent benchmark queries in inferential comparisons.

The 40-query review is exploratory. State its sample size and stratification explicitly, and do not generalize it to all users, institutions, languages, or agent systems. A larger validation study would be needed for stronger reliability claims.

## Data handling

Use only fictional synthetic benchmark records. Do not upload real student records, names, grades, fee status, or other personally identifiable education data to third-party LLM services or annotation platforms without institutional authorization, an appropriate legal basis, consent where required, and data-protection safeguards. Store annotation files in access-controlled project storage.
