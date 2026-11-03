# Research Proposal — Dalian Maritime University (Version 2, 3 November 2026)

**Applicant:** Muhammad Faizan Sajid  
**Proposed degree:** Master's in Computer Science / Artificial Intelligence (exact programme subject to DMU confirmation)  
**Prospective supervisor:** Professor Xie Xinqiang  
**Working title:** **Evaluating the Accuracy and Trustworthiness of Retrieval-Augmented AI Agents for Structured Question Answering**  
**Status:** Supervisor-discussion draft; includes completed *no-Jev* preliminary results. Not a completed thesis or a claim of verified general agent reasoning.

## Abstract

Large language model (LLM) agents can retrieve records, select entities, and generate natural-language answers, yet answer correctness alone does not establish trustworthiness. A correct-looking answer may be unsupported by retrieved evidence, and an agent may answer when the source is ambiguous or lacks the requested information. This proposal investigates a reproducible, multidimensional approach to evaluating *observable* reasoning behaviour in retrieval-augmented agents: final-answer correctness, evidence support, entity-resolution decisions, appropriate clarification or abstention, repeatability, and operational cost. A student-record question-answering system with a controlled fictional relational database provides the initial testbed. Three conditions are compared: baseline retrieval-augmented generation (A), deterministic post-generation requested-field verification (B), and verification plus a pre-generation evidence-availability gate (C). A completed no-Jev experiment comprises 200 queries, five repeated executions per condition, and 3,000 predictions. Preliminary paired, category-stratified bootstrap analysis indicates small, uncertain differences in decision and exact-answer correctness, alongside lower measured latency for B and C. These results motivate deeper evaluation of evidence faithfulness and decision quality rather than an unsubstantiated claim that verification improves accuracy. The proposed Master's research will validate human-grounded trustworthiness metrics, investigate failure modes and robustness, and assess how well the evaluation approach transfers beyond the initial testbed.

## 1. Background and motivation

LLM-based agents increasingly combine language generation with retrieval, tools, and structured data. Their apparent fluency does not guarantee that they identify the right entity, retrieve the right record, faithfully use evidence, or refrain from answering when evidence is missing. Accuracy and trustworthiness therefore need separate, observable measures.

Professor Xie Xinqiang has suggested that my research focus on **evaluating both the accuracy and trustworthiness of agent reasoning**, with flexibility to design the approach. I interpret this as a methodological research question: what observable evidence demonstrates that an agent's *answer and decision process* are reliable? The project will inspect recorded actions, retrieved evidence, structured verifier outcomes, and final responses; it will **not** claim to measure inaccessible internal chain-of-thought or prove causal faithfulness from generated explanations alone.

My undergraduate final-year project, *Centralized University Information System Using Generative AI*, integrated MySQL, LangChain, ChromaDB, sentence-transformer embeddings, Groq-hosted generation, and Streamlit. The prototype provides a realistic starting point for controlled experiments, but the proposed contribution is an **evaluation framework**, not a new student-record chatbot.

## 2. Problem statement and research gap

A single accuracy score can obscure distinct failures:

- **Wrong entity:** evidence is retrieved for a different student.
- **Retrieval failure:** a database value exists but is absent from the retrieved context.
- **Unsupported answer:** the output asserts a value that is absent from or contradicted by the retrieved evidence.
- **Unwarranted answer:** the agent answers despite an ambiguous entity or genuinely absent source value.
- **Unnecessary abstention:** the agent declines when sufficient authorized evidence exists.
- **Operational failure:** an API or infrastructure error is mistakenly counted as an intentional abstention.

Existing work on RAG evaluation and selective question answering motivates these distinctions, but the present study must empirically establish whether its proposed measurements are valid and useful in the selected structured-QA setting. It does not assume novelty merely from combining existing metrics. A further gap for this specific implementation is that exact matching and decision classification do not, by themselves, establish semantic correctness or evidence faithfulness.

## 3. Aim, objectives, and research questions

**Aim:** Develop and assess a reproducible protocol for evaluating the accuracy and trustworthiness of observable decisions and outputs of retrieval-augmented AI agents.

**Objectives:** (i) operationalize separate measures of correctness, grounding, and decision appropriateness; (ii) validate a fictional-record benchmark against an isolated database; (iii) compare controlled agent conditions and repeated outcomes; (iv) validate automatic scores against independent human judgments; (v) analyze robustness, failure modes, and latency/coverage trade-offs.

**RQ1.** How can final-answer correctness be evaluated separately from the support provided by retrieved evidence?

**RQ2.** How accurately do automatic decision and requested-field verification metrics agree with human assessments of answer correctness, evidence support, and appropriate abstention?

**RQ3.** What incremental effects do post-generation evidence verification (A→B) and pre-generation evidence-availability gating (B→C) have on unsupported answers, answer coverage, decision quality, and latency?

**RQ4.** How stable are these measures across repeated executions and across answerable, ambiguous-entity, and genuinely missing-information cases?

**RQ5 (extension, conditional on time/resources).** How robust is the evaluation protocol to retrieval omissions, misleading or conflicting evidence, and a second structured-data task?

No hypothesis of guaranteed improvement is assumed. The analysis will report both beneficial and adverse trade-offs.

## 4. Existing experimental foundation

### 4.1 Controlled testbed

The system uses a relational student database, scoped retrieval, local entity matching, role-based access control (RBAC), and an LLM response component. Experimental records are fictional. The benchmark contains **200 queries**: **100 answerable**, **50 ambiguous-entity**, and **50 source-missing**. The protocol distinguishes recognized but absent source fields from unsupported schema fields and retrieval failures. Benchmark validation against a frozen database snapshot is required by the experiment runner; the final submission should attach the actual validation manifest/hash and verify that the tested snapshot matches it.

### 4.2 Conditions and causal contrasts

- **A — Baseline RAG:** local candidate matching, RBAC, scoped retrieval, and response generation, without the experimental post-generation verifier.
- **B — Evidence-verified RAG:** A plus a deterministic post-generation check for the requested recognized field/value in retrieved evidence and generated output. This is a narrow verifier, **not** a universal factuality checker.
- **C — Evidence-gated RAG:** B plus a pre-generation gate that abstains when the requested recognized field is unavailable in evidence, subject to the implementation's source-state checks.

All conditions share the same synthetic snapshot, candidate matching, ambiguity clarification, authorization, retrieval settings, and model configuration. Clarification is a **shared** safeguard, not a unique improvement due to C. A→B measures the additional verifier under the tested configuration; B→C measures the additional gate. Confounding from execution order, caching, and API variability must still be considered.

### 4.3 Completed no-Jev experiment and preliminary results

The completed **no-Jev** run contains **200 cases × 5 repetitions × 3 systems = 3,000 prediction records**. This is a distinct ablation in which the external Jev candidate-resolution call is disabled; it is **not** evidence about Jev-enabled performance. Five regression tests for repeated-file loading passed locally. The paired query-level, category-stratified bootstrap used **4,000 resamples**, seed **20261101**, and treated each query as the inferential unit, averaging repeated correctness observations within query.

Differences below are **right minus left**; for latency, negative values mean the right-hand system was faster. Correctness values are percentage-point differences. Latency is the difference in *per-query median latency* aggregated across queries, not necessarily the difference in global median response time.

| Comparison | Decision correctness (95% CI) | Exact-answer correctness (95% CI) | Latency, ms (95% CI) |
|---|---:|---:|---:|
| B − A | +0.3 pp (−0.8, +1.2) | 0.0 pp (−0.8, +0.8) | −513.7 (−649.3, −381.9) |
| C − B | +0.2 pp (0.0, +0.5) | +0.2 pp (−0.4, +0.8) | −196.9 (−321.3, −75.1) |
| C − A | +0.5 pp (−0.4, +1.3) | +0.2 pp (−0.6, +1.0) | −710.6 (−841.8, −576.9) |

Decision and latency comparisons use **200 queries**; exact-answer correctness comparisons use **100 answerable queries**. The C−B decision interval touches zero at reported precision and must not be described as decisive. Most correctness intervals include zero. Latency differences are clearer, but their mechanism is **not established** by bootstrap inference. These results do **not** demonstrate reduced hallucination or improved evidence faithfulness; those require the planned review below. Raw local experiment files and analysis output should be retained as provenance and not committed if they contain diagnostics.

## 5. Proposed Master's methodology

### 5.1 Evaluation constructs and operational definitions

**Answer accuracy:** exact match against benchmark answers, supplemented by semantic human adjudication for legitimate paraphrases. Report both accuracy among answered cases and correct-answer rate over all answerable cases so abstention cannot artificially inflate accuracy.

**Decision appropriateness:** agreement between the observed *answer / clarify / abstain* action and benchmark expectations, with category-specific confusion matrices, clarification and abstention precision/recall, unnecessary non-answer rate, and unsafe-answer rate.

**Evidence faithfulness:** independent judgment of whether each material factual claim in the final answer is supported by the *actual retrieved evidence* available to that execution. Distinguish supported, contradicted, insufficient evidence, and not applicable. Correctness against the source database and support by retrieved evidence must be scored separately.

**Source-state awareness:** distinguish genuinely absent fields in the database from retrieval omissions and unsupported schema fields. Record retrieval and verifier diagnostics where available.

**Reliability and efficiency:** consistency across five repeats, operational error counts, answer coverage, and response latency (including distribution summaries). Evaluate access-control violations as a separate safety outcome rather than assuming zero leakage.

A candidate composite trustworthiness index may be explored **only after** its components and weights are justified and validated against human judgment; the primary report will preserve disaggregated metrics.

### 5.2 Human evaluation protocol

Select a **stratified sample of 40 unique queries**: 20 answerable, 10 ambiguous, and 10 source-missing. Two independent reviewers will evaluate up to **600 output-level observations** (40 queries × 5 repeats × 3 systems), blinded to condition where feasible. The rubric will record: correct entity, final-answer correctness, evidence support/contradiction, evidence sufficiency, action appropriateness, and unsupported factual claims. Include written examples and an adjudication procedure before scoring. Report raw agreement and Cohen's kappa for suitable categorical labels, with caveats about prevalence and the exploratory sample size. If reviewer capacity is limited, predefine a smaller representative sample and disclose the reduced power rather than silently changing the protocol.

### 5.3 Experimental and statistical analysis

Audit case IDs, repetitions, dataset hash, database snapshot, model/configuration metadata, operational failures, and source-evidence diagnostics before interpreting results. Report per-category denominators and both absolute rates and paired differences. Use paired, category-stratified query-level bootstrap confidence intervals; do not treat repeated attempts as independent queries. Inspect anomalous cases manually. Interpret intervals as uncertainty estimates, not proof of equivalence or causal mechanisms. Preserve separate reporting for no-Jev and any future Jev-enabled conditions; never pool them without an explicit factorial design.

### 5.4 Extensions and generalization

If feasible, introduce controlled retrieval omissions and conflicting evidence to test whether metrics distinguish retrieval failure from unsupported generation. A second synthetic structured-data domain or a small instrumented tool-using workflow would test transferability. These extensions are **proposed**, not completed, and should be narrowed with Professor Xie based on programme duration and resources. Urdu/Pashto evaluation remains a possible later extension, not a core promise.

## 6. Expected contributions and limitations

Expected contributions are: (1) an explicit multidimensional evaluation rubric for observable agent outputs and decisions; (2) a database-validated synthetic benchmark with failure categories; (3) paired comparative evidence about verification and abstention mechanisms; (4) agreement analysis between automatic and human trustworthiness judgments; and (5) reproducible protocols, scripts, and documented failure cases.

Limits include synthetic institutional records, a narrow deterministic verifier, rule-based decision classification, possible retrieval confounding, external-model variability, and limited human-review size. A correct answer does not prove faithful reasoning, a grounded answer does not necessarily imply source truth, and an observed trace does not expose hidden internal reasoning. Generalization to autonomous multi-step agents must be evaluated rather than assumed.

## 7. Ethics and reproducibility

Use only fictional student records in experiments. Keep research fixtures isolated from real institutional data; retain RBAC and avoid exposing real personal records to external LLM APIs. Document model versions, prompts, embedding/retrieval settings, seeds, benchmark hash, source database snapshot, run ordering, and operational errors. Publish only safe synthetic fixtures, analysis code, rubrics, and suitably reviewed aggregate results.

## 8. Provisional Master's study plan

**Months 1–3:** Review literature on agent evaluation, RAG faithfulness, selective prediction, and tool-use assessment; refine constructs and hypotheses with supervisor.  
**Months 4–6:** Audit and freeze benchmark and metadata; finalize annotation rubric and experimental protocol.  
**Months 7–10:** Complete evidence-support human review and diagnostic error analysis; refine automated evaluation.  
**Months 11–15:** Run controlled robustness tests and, if feasible, a second task/domain; conduct paired statistical analysis.  
**Months 16–20:** Analyze reliability, reviewer agreement, limitations, and transferability; prepare a manuscript if findings justify it.  
**Months 21–24:** Write and revise Master's thesis and reproducibility package.

This is a provisional **24-month research schedule**, to be adjusted to the actual DMU programme duration and Professor Xie's guidance. Previously completed preliminary work will be revalidated as needed rather than represented as future work.

## 9. Preparation and supervisor alignment

I completed a BS in Computer Science at the University of Agriculture Peshawar in July 2025 (CGPA **3.44/4.00**). My A+-graded final-year project established practical experience with RAG, relational databases, and LLM applications. Subsequent work on controlled synthetic experiments, reproducible analysis, and explicit failure categories motivates a transition from system implementation to rigorous evaluation research.

The proposal is intended for discussion with **Professor Xie Xinqiang at Dalian Maritime University**, reflecting his communicated emphasis on the accuracy and trustworthiness of agent reasoning. I welcome his guidance on whether to retain structured RAG as the primary setting or extend earlier to tool-using agents. His acceptance letter and research encouragement do not by themselves establish university admission or programme requirements.

## 10. Selected foundational references (bibliographic details to verify before submission)

1. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS.
2. Es, S., et al. (2024). *RAGAS: Automated Evaluation of Retrieval Augmented Generation*. EACL System Demonstrations.
3. Saad-Falcon, J., et al. (2024). *ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems*. NAACL.
4. Kamath, A., et al. (2020). *Selective Question Answering under Domain Shift*.

**Before submission:** expand and verify recent literature on *agent trajectory/tool-use evaluation* and *faithfulness*, verify exact bibliographic metadata and university formatting, and attach the actual experimental provenance. The references above are carried over from the existing repository draft, not presented as a newly completed systematic literature review.

## Research provenance and document status

- Prior DMU draft: `docs/proposals/DMU_Professor_Xie_Research_Proposal.md`.
- Concise DMU concept: `docs/PROPOSAL_DALIAN_MARITIME_XIE_XINQIANG.md`.
- Experiment design: `docs/RESEARCH_EXPERIMENT_V2.md` and `scripts/run_repeated_research_experiment.py`.
- Bootstrap implementation: `scripts/analyze_repeated_experiment.py`.
- Preliminary result source: local `experiments/results/no_jev_primary_200x5_v1/bootstrap_analysis.json` output supplied by the researcher on 3 November 2026; not checked into GitHub.
- **Status distinction:** experiment and bootstrap completed; human evidence-faithfulness adjudication, broader agent tasks, literature verification, and final supervisor review remain pending.
