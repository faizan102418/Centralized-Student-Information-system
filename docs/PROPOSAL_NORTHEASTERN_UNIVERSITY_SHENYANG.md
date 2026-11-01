# Research proposal — Northeastern University, Shenyang (CSC application draft)

## Proposed title
**Evaluating the Accuracy and Trustworthiness of Retrieval-Augmented AI Agents for Structured Question Answering**

## 1. Background and motivation
Large language model (LLM)-based agents can translate natural-language questions into actions over external information sources. In structured question-answering settings, however, fluent responses may still be inaccurate, insufficiently supported by retrieved records, or overconfident when the requested information is unavailable. These failure modes are consequential in information systems that expose structured records and require reliable, auditable answers.

My undergraduate final-year project, a centralized student-information assistant, provided a practical starting point. I developed a retrieval-augmented prototype combining a relational student database, vector retrieval, sentence-transformer embeddings, LangChain, and an LLM-based response component. The system answers questions about student records using retrieved database evidence and includes role-based access controls. This experience motivates a focused research question: how can the accuracy and trustworthiness of retrieval-augmented agents be evaluated systematically, and which lightweight verification and decision mechanisms improve their observable reliability?

## 2. Research aim and questions
The aim is to design and evaluate an experimental framework for assessing answer accuracy, evidence support, and decision appropriateness in retrieval-augmented agents for structured question answering.

The study will address:
1. How accurately do retrieval-augmented agents answer structured questions when the required source information is available?
2. To what extent are generated answers supported by retrieved evidence?
3. How do post-generation evidence verification and a pre-generation evidence-availability gate affect answer correctness, unsupported answers, abstention behaviour, and system performance?
4. How reliably can the agent distinguish answerable, ambiguous-entity, and genuinely missing-information queries?

## 3. Proposed methodology
### 3.1 Experimental testbed and benchmark
I will use a controlled student-information database as an initial experimental testbed. It will contain fictional records only. A benchmark will include answerable questions, ambiguous-name questions with multiple valid candidate records, and missing-information questions in which a recognized database field is unavailable because the relevant source record is absent. Each expected action and answer will be checked against a frozen database snapshot before evaluation.

### 3.2 System conditions
Three conditions will be compared under the same database snapshot, model, retrieval configuration, local entity matching, ambiguity clarification, and authorization controls:
- Baseline: retrieval-augmented generation without the experimental evidence verifier.
- Evidence verification: baseline plus a deterministic post-generation check that verifies whether the generated answer contains the requested structured value found in retrieved evidence.
- Evidence-availability gate: the second condition plus a pre-generation gate that abstains before generation when a recognized requested field is absent from retrieved evidence.

The interventions are deliberately scoped. The deterministic verifier checks a requested field/value relationship; it is not a general-purpose fact checker. The study will evaluate observable agent behaviour rather than claim access to hidden model reasoning.

### 3.3 Repeated experiments
Each query will be executed five times under each condition to examine output variability. The dataset, database snapshot, prompt, retrieval settings, model configuration, and experimental environment will be recorded. Execution order will be rotated to reduce systematic order effects. Operational failures will be logged separately and not counted as abstentions.

### 3.4 Evaluation
Evaluation will include decision accuracy for answer, clarify, and abstain actions; exact answer accuracy and answer coverage on answerable queries; unsafe-answer rate on ambiguous and missing-information queries; clarification and abstention precision/recall; evidence-support ratings from independent human reviewers; and latency and decision consistency across repeated executions.

The query will be the statistical unit. Repeated outputs will be treated as nested observations. Paired query-level comparisons and bootstrap confidence intervals will be used where appropriate. A stratified human-review sample will be independently rated by two reviewers using a predefined rubric for answer correctness, evidence support, and decision appropriateness.

## 4. Expected contributions
The expected outcomes are:
1. A reproducible benchmark design that distinguishes source-level missing information from unsupported fields, ambiguous entities, and retrieval failures.
2. An empirical comparison of baseline generation, post-generation evidence verification, and a pre-generation evidence-availability gate.
3. A practical evaluation protocol combining automated decision/answer metrics with human assessment of evidence support.
4. An open and documented experimental implementation that can be extended to other structured information domains.

The work is intended as a focused evaluation study and will not assume that improvements on a synthetic student database automatically generalize to other domains. Generalization will require additional datasets and schemas.

## 5. Feasibility and preparation
My BS in Computer Science (University of Agriculture Peshawar, 2025; CGPA 3.44/4.00) provided a foundation in algorithms, databases, software engineering, and AI-related coursework. My final-year project received an A+ and gave me practical experience integrating a relational database with retrieval and LLM components. I have also completed foundational machine-learning training. The existing prototype and synthetic benchmark provide a starting implementation; the proposed work will focus on rigorous benchmark validation, controlled experiments, and trustworthy evaluation rather than claiming a completed research result.

## 6. Proposed schedule
- Months 1–2: review literature on LLM-agent evaluation, RAG evaluation, factuality, selective prediction, and abstention; refine research questions and protocol.
- Months 3–4: validate and extend the benchmark; freeze database fixtures, system conditions, and evaluation rubric.
- Months 5–7: implement and run repeated experiments; inspect errors and verify reproducibility.
- Months 8–9: conduct independent human validation and statistical analysis.
- Months 10–12: interpret findings, document limitations, prepare thesis and research dissemination.

## 7. Fit and supervision
I hope to pursue this work within Northeastern University, Shenyang's relevant computer science and artificial-intelligence research environment. The proposed topic can be refined with the prospective supervisor to align with the group's current work in intelligent systems, information retrieval, and trustworthy AI. The final submission should be tailored to the supervisor and the university's current CSC research-proposal template and word/page requirements.

## References
A final reference list should be added after the literature review and verified against the university's required citation style. Key literature areas include RAG evaluation, factual consistency and attribution, selective question answering, and evaluation of LLM-based agents.
