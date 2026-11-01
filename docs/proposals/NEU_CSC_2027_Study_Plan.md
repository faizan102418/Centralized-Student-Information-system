# Research Proposal / Study Plan — Northeastern University (CSC Type-B, 2027)

**Applicant:** Muhammad Faizan Sajid  
**Proposed degree:** Master's degree (exact programme title to be selected from Northeastern University's 2027 international master's programme list)  
**Proposed field:** Computer Science / Artificial Intelligence  
**Proposed research title:** Evaluating the Accuracy and Trustworthiness of Retrieval-Augmented AI Agents for Structured Question Answering  
**Supervisor:** To be confirmed with the relevant NEU department or research group

## 1. Research background and motivation

Large language models (LLMs) have made natural-language interfaces to information systems increasingly capable. Retrieval-augmented generation (RAG) combines a language model with an external source of information so that responses can be grounded in retrieved documents or database records. This is particularly relevant to structured information systems, where a user may ask questions about a student's academic programme, scholarship, or fee record without knowing the underlying database schema or query language.

However, fluent responses are not necessarily correct or trustworthy. An agent may retrieve the wrong entity, overlook a relevant field, produce an unsupported value, or answer when the source does not contain the requested information. It may also fail to recognize when a query is ambiguous and should request clarification. These failures are consequential in domains such as education administration, public services, healthcare administration, and enterprise information management, where users may rely on answers to make decisions.

My interest in this topic developed through my Bachelor of Science in Computer Science at the University of Agriculture Peshawar, Pakistan, where I graduated in July 2025 with a CGPA of 3.44/4.00. My final-year project, a Centralized University Information System Using Generative AI, explored a RAG-based interface to student information. The prototype connected a MySQL database to a vector retrieval component and an LLM, using LangChain, ChromaDB, sentence-transformer embeddings, Groq-hosted inference, and Streamlit. The project helped me understand the practical difficulties of entity resolution, evidence retrieval, database integration, and multilingual question answering. In particular, queries in Urdu and Pashto were less reliable than English queries, motivating a longer-term interest in trustworthy AI for structured and multilingual information access.

For master's study at Northeastern University (NEU), I propose to build on this practical foundation and study methods for evaluating the accuracy and trustworthiness of retrieval-augmented AI agents. The research will focus on observable agent behaviour rather than attempting to infer hidden model reasoning. It will examine whether an agent gives a correct answer, whether the answer is supported by the available evidence, and whether it chooses an appropriate action when evidence is ambiguous or unavailable.

## 2. Research problem

Existing RAG systems are commonly assessed through answer relevance, correctness, retrieval quality, or model-based evaluation. These measures are useful but do not always capture whether an agent should answer, ask a clarifying question, or abstain. A system may produce a plausible answer despite retrieving incomplete evidence. Conversely, it may refuse a question whose answer is present in the database but was not retrieved. These cases should be distinguished because they represent different reliability problems.

This study will investigate a structured question-answering setting in which a user asks about a particular record and a defined field. The research problem is to design a reproducible evaluation framework that separates answer correctness, evidence support, entity ambiguity, source-level missing information, retrieval failure, and operational failure. It will then test whether deterministic evidence verification and source-aware selective decisions improve the trustworthiness of agent outputs without creating unacceptable losses in answer coverage or efficiency.

## 3. Research aim and questions

The overall aim is to evaluate the accuracy and trustworthiness of retrieval-augmented AI agents for structured database question answering.

The study will address four questions:

1. How can answer accuracy and evidence support be measured separately in structured database question-answering agents?
2. To what extent does deterministic post-generation evidence verification reduce unsupported or conflicting answers?
3. Does a source-aware selective decision layer improve the agent's ability to abstain when a recognized field is genuinely absent from the source database?
4. What trade-offs arise among answer accuracy, answer coverage, appropriate clarification and abstention, and response latency?

## 4. Proposed methodology

### 4.1 Experimental testbed and benchmark

The initial testbed will be based on my existing university-information RAG prototype. It uses a structured MySQL database, ChromaDB retrieval, sentence-transformer embeddings, and an LLM-based answer-generation component. The experimental database will contain fictional records only. No real student records or personally identifiable educational data will be used.

I have prepared a synthetic benchmark of 200 queries with three categories: 100 answerable queries, 50 ambiguous-entity queries, and 50 source-missing queries. The source-missing cases are being redesigned to use recognized schema fields that are genuinely NULL or whose related database records are absent. A database-validation script will check each case against the isolated synthetic database before experimental runs. Unsupported fields and retrieval failures will be recorded as separate categories rather than being counted as genuine missing values.

### 4.2 System conditions

Three controlled conditions will be compared:

- **System A — Baseline RAG:** entity matching, access control, retrieval, and LLM answer generation, without the experimental post-generation evidence verifier.
- **System B — RAG with evidence verification:** System A plus a deterministic verifier that checks whether the answer contains the value for the requested recognized field in the retrieved evidence. This verifier is deliberately narrow; it is not presented as a general-purpose fact checker.
- **System C — Evidence verification with source-aware selective decisions:** System B plus a pre-generation source-state check. For a recognized field, the system checks only whether a non-empty value or related source record exists. It abstains when the source value is genuinely absent, and it distinguishes this from an unavailable retrieval result. The check does not return the database value to the user and does not replace the RAG answer-generation process.

Entity ambiguity clarification and role-based access control will remain common safeguards in all three systems. Therefore, clarification is measured as a shared behaviour, not claimed as a unique contribution of System C. This design isolates the incremental effect of evidence verification (A versus B) and the additional source-aware decision gate (B versus C).

### 4.3 Repeated experiments and measurements

Each query will be executed five times per system, producing up to 3,000 system attempts across the 200-query benchmark. The dataset version, database snapshot, model identifier, embedding model, retrieval settings, prompts, and experimental configuration will be recorded. Runs will be labelled explicitly, and condition order will be rotated to reduce fixed-order effects. Operational errors will be logged separately rather than being treated as abstentions.

The evaluation will report answer exact-match accuracy, answer coverage on answerable queries, correct-answer rate across all answerable queries, decision accuracy, clarification precision and recall, missing-information abstention precision and recall, and response latency. Evidence support will be evaluated separately because an answer can be textually correct but not supported by the retrieved evidence. Repeated observations will be aggregated within query; the query will remain the unit of statistical analysis. Paired, category-stratified bootstrap confidence intervals will be used to estimate differences between systems. Any semantic paraphrases missed by exact matching will be reviewed manually.

### 4.4 Human validation

A stratified sample of 40 unique queries will be selected for human review: 20 answerable, 10 ambiguous, and 10 source-missing. Two reviewers will independently assess all five runs from all three systems, resulting in up to 600 output annotations. They will judge action appropriateness, answer correctness, evidence support, evidence sufficiency, and unsupported factual claims using a written rubric. Cohen's kappa and raw agreement will be reported for the independent categorical annotations. This review will be described as exploratory because of its limited sample size.

## 5. Expected outcomes and contribution

The expected outcome is a reproducible evaluation framework for structured RAG agents that separates answer correctness from evidence support and decision appropriateness. The experiment should clarify whether a narrow verifier reduces unsupported answers, whether source-aware abstention handles genuine missing information more reliably, and what these safeguards cost in terms of coverage and latency. The work will also produce a validated synthetic benchmark, experiment scripts, annotation guidance, and documented limitations.

The contribution is not a claim that a deterministic field check solves general agent reasoning. Rather, it is a controlled study of measurable behaviours that are important to trustworthy agents. The framework may provide a foundation for future work on more complex multi-step agents, multilingual queries, and additional data domains. The Urdu and Pashto limitations observed in my undergraduate project are a possible future direction, but multilingual evaluation will not be included in the core scope unless the master's research schedule and resources permit it.

## 6. Study plan at Northeastern University

During the initial stage of the master's programme, I intend to strengthen my foundations in artificial intelligence, machine learning, information retrieval, databases, research methodology, and statistical evaluation. I will review recent literature on RAG evaluation, selective question answering, evidence attribution, and trustworthy AI, and refine the research questions with the guidance of an NEU supervisor.

In the next stage, I will audit the database schema and benchmark, finalize the controlled system definitions, implement the experimental conditions, and conduct pilot runs. The pilot will be used to identify implementation errors and refine the annotation rubric before the full experiment. I will then conduct repeated runs, analyze the results at the query level, and carry out the planned human validation.

In the final stage, I will interpret the findings, document limitations, prepare a master's thesis, and aim to submit suitable results to a relevant academic conference or journal, subject to the quality and novelty of the findings. The precise timeline will be aligned with the duration and requirements of the master's programme to which I am admitted.

## 7. Suitability and motivation

My undergraduate training in computer science provided a foundation in programming, data structures, algorithms, databases, software engineering, and artificial intelligence. Through my final-year project, I gained practical experience integrating a structured database with retrieval and generative components. I now want to move from building a working prototype toward conducting a carefully controlled research study. Master's study at NEU would allow me to deepen my theoretical understanding, develop stronger research skills, and work with academic supervision in computer science and artificial intelligence.

I am particularly motivated to contribute to reliable AI systems that can communicate uncertainty and avoid unsupported claims. I understand that the proposed work will require refinement in consultation with the assigned supervisor and alignment with the exact programme and research facilities available at NEU. I am prepared to adapt the scope while preserving the central objective of rigorous accuracy and trustworthiness evaluation.

## References

1. Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems*.
2. Es, S. et al. (2024). RAGAS: Automated Evaluation of Retrieval Augmented Generation. *Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations*.
3. Saad-Falcon, J. et al. (2024). ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. *Proceedings of NAACL-HLT*.
4. Kamath, A. et al. (2020). Selective Question Answering under Domain Shift.
