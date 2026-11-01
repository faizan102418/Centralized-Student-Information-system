# Research proposal — Dalian Maritime University (Professor Xie Xinqiang)

## Proposed title
**Evaluating the Accuracy and Trustworthiness of Retrieval-Augmented AI Agents for Structured Question Answering**

## 1. Research background
LLM-based agents increasingly retrieve external information and use it to answer questions or support decisions. Their fluency does not guarantee correctness: an agent may select the wrong entity, produce an answer that is not supported by its evidence, or answer confidently when the relevant information is missing. Evaluating these observable failure modes is essential to understanding the accuracy and trustworthiness of agent systems.

Professor Xie Xinqiang has advised me to focus primarily on evaluating the accuracy and trustworthiness of agent reasoning, while allowing me to design the research approach independently. I interpret this direction as an opportunity to study how agent decisions and final answers can be evaluated against external evidence. The proposed work therefore focuses on observable reasoning outcomes—answer correctness, evidence support, and answer/clarify/abstain decisions—rather than attempting to infer or score hidden chain-of-thought.

## 2. Aim and research questions
The aim is to develop a reproducible evaluation framework for the accuracy and trustworthiness of retrieval-augmented agents in structured question-answering tasks.

The research questions are:
1. How should the accuracy and trustworthiness of a retrieval-augmented agent be operationalized and measured?
2. How often are agent answers correct and supported by the retrieved source evidence?
3. What effect does deterministic post-generation evidence verification have on unsupported answers and answer accuracy?
4. Does adding a pre-generation evidence-availability gate improve the appropriateness and efficiency of answer/abstain decisions when requested information is missing?
5. How stable are these outcomes across repeated executions?

## 3. Research design
### 3.1 Testbed and benchmark
An existing student-information assistant will serve as the initial testbed. It combines a relational database, vector retrieval, sentence-transformer embeddings, and an LLM response component. A controlled benchmark of fictional records will include answerable queries, ambiguous queries where a partial name matches multiple records, and missing-information queries where a recognized field is absent because its related source record does not exist.

Benchmark labels will be validated against a frozen database snapshot. Unsupported schema fields and retrieval failures will be tracked separately from genuine source-level missing information.

### 3.2 Comparative agent conditions
Three conditions will be evaluated while holding entity matching, ambiguity clarification, authorization, data snapshot, model, and retrieval settings constant:
- A — baseline RAG agent: generation from retrieved evidence without the experimental post-generation verifier.
- B — evidence-verified agent: A plus a deterministic post-generation check that the requested field value is present in retrieved evidence and in the generated answer.
- C — evidence-gated agent: B plus a pre-generation gate that abstains before LLM generation when a recognized requested field is absent from retrieved evidence.

The design isolates two effects: A–B estimates the contribution of post-generation evidence verification; B–C estimates the additional contribution of early evidence-availability gating. Ambiguity clarification is common to all conditions and will not be presented as an incremental effect of C.

### 3.3 Evaluation protocol
The benchmark will be executed five times per query and condition. The evaluation will record raw responses, observable decisions, model and configuration metadata, verifier outcomes, and latency. The primary measures will include answer correctness and answer coverage; decision accuracy; evidence support assessed through human review; unsafe-answer rate on ambiguous and missing cases; clarification and abstention precision/recall; and decision consistency and latency across repeats.

A stratified sample of 40 unique queries will undergo independent review by two reviewers. They will assess answer correctness, evidence support, and decision appropriateness using a documented rubric. Inter-rater agreement and adjudicated labels will be reported. Statistical comparisons will treat the query as the unit of analysis and retain paired system outcomes when resampling.

## 4. Expected outcomes
The research is expected to produce a clear operational definition of accuracy and trustworthiness for this structured QA setting, a validated benchmark that distinguishes different failure types, and empirical evidence about the effects and limitations of evidence verification and early abstention. The resulting framework and implementation may provide a foundation for further evaluation across other agent tasks and datasets.

The study will explicitly limit its claims to the selected testbed and measured behaviours. A narrow field/value verifier cannot guarantee that every claim in a response is supported, and absence from retrieved evidence can reflect retrieval failure rather than source-level absence. These limitations will be addressed through database-backed benchmark validation and human review.

## 5. Preparation and feasibility
I completed a BS in Computer Science at the University of Agriculture Peshawar in 2025 (CGPA 3.44/4.00). My final-year project, a centralized student-information assistant using database retrieval and LLM generation, received an A+. This work gives me an implemented prototype and practical experience with database-backed RAG systems. I now aim to extend that implementation into a more rigorous research study centred on evaluation, evidence support, and trustworthy agent decisions.

## 6. Provisional timeline
- Months 1–2: literature review and refinement of evaluation constructs.
- Months 3–4: benchmark validation, dataset documentation, and protocol freeze.
- Months 5–7: implementation and repeated comparative experiments.
- Months 8–9: human validation, error analysis, and statistical evaluation.
- Months 10–12: thesis writing, revision with supervisor, and dissemination.

## 7. Supervision alignment
This proposal is designed to align with Professor Xie's suggested direction of evaluating agent reasoning accuracy and trustworthiness. I would welcome his guidance in refining the evaluation dimensions, selecting suitable agent tasks, and extending the testbed beyond structured student-record question answering if that would better fit the group's research priorities.
