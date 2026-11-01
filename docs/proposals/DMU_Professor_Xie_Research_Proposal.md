# Research Proposal — Dalian Maritime University

**Applicant:** Muhammad Faizan Sajid  
**Proposed degree:** Master's degree in Computer Science / Artificial Intelligence (subject to DMU programme availability and admission)  
**Proposed supervisor:** Professor Xie Xinqiang  
**Research title:** Evaluating the Accuracy and Trustworthiness of Retrieval-Augmented AI Agents for Structured Question Answering

## 1. Background and motivation

Large language models have made it possible to build agents that interact with external tools, databases, and knowledge sources to answer user questions. Yet the fluency of an agent's response does not guarantee that its answer is correct, that the evidence supports it, or that it has taken the right action when the information is incomplete. Evaluating the accuracy and trustworthiness of agent reasoning is therefore an important research problem.

Professor Xie Xinqiang has advised me to focus mainly on how to evaluate both the accuracy and trustworthiness of agent reasoning, while allowing me to design the research approach according to my own understanding. I interpret this direction as an opportunity to study the observable outcomes of agent reasoning in a controlled setting. Rather than attempting to inspect or score hidden chain-of-thought, I propose to evaluate whether an agent resolves the correct entity, retrieves relevant evidence, produces an answer supported by that evidence, and selects an appropriate action when it cannot safely answer.

My interest is based on my undergraduate work at the University of Agriculture Peshawar, Pakistan. I completed a Bachelor of Science in Computer Science in July 2025 with a CGPA of 3.44/4.00. My final-year project, Centralized University Information System Using Generative AI, developed a question-answering prototype over student information. It combined MySQL, LangChain, ChromaDB, sentence-transformer embeddings, Groq-hosted LLM inference, and Streamlit. Through this project, I gained practical experience with structured data, retrieval, entity matching, prompt construction, and the limitations of generated answers. I also observed weaker performance for Urdu and Pashto queries than for English queries. These experiences led me to consider reliability evaluation as a more fundamental next step than simply adding further features to the prototype.

## 2. Research problem

A retrieval-augmented agent may fail in several distinct ways. It may retrieve evidence about the wrong entity, fail to retrieve a field that exists in the database, generate a value that conflicts with the evidence, or provide a confident answer when the source contains no such information. It may also fail to ask for clarification when a name matches multiple records. These cases should not be collapsed into one general measure of accuracy.

This research will investigate how to evaluate the accuracy and trustworthiness of a retrieval-augmented agent for structured database question answering. The work will distinguish at least five dimensions: (1) answer correctness, (2) evidence support, (3) entity-resolution and clarification behaviour, (4) source-aware abstention, and (5) operational performance. The purpose is to create a reproducible evaluation approach and determine which lightweight safeguards improve reliability under controlled conditions.

## 3. Aim and research questions

The main aim is to develop and evaluate a practical framework for assessing the accuracy and trustworthiness of retrieval-augmented AI agents.

The research questions are:

1. How can the accuracy of an agent's final answer be evaluated independently from the support provided by its retrieved evidence?
2. How effectively can a deterministic evidence verifier detect answers that conflict with or are not supported by retrieved structured records?
3. Does adding a source-aware selective decision mechanism improve an agent's ability to abstain when a requested field is genuinely missing?
4. What trade-offs do these safeguards introduce in answer coverage, clarification and abstention behaviour, latency, and operational reliability?

## 4. Research methodology

### 4.1 Testbed and synthetic benchmark

The study will use a university student-information RAG prototype as a controlled experimental testbed. The system contains a MySQL database with general student information, scholarship records, and fee records. It uses deterministic candidate matching, role-based access control, ChromaDB vector retrieval, sentence-transformer embeddings, and an LLM for response generation. All experimental records will be fictional. Real student information will not be sent to third-party model services.

A 200-query synthetic benchmark is being prepared with 100 answerable cases, 50 ambiguous-entity cases, and 50 source-missing cases. The missing-information cases will use recognized database fields whose values are NULL or whose related records are absent. Each case will be validated against the isolated synthetic database snapshot. Unsupported schema fields, retrieval failures, and source-level missing values will be labelled separately. This distinction is necessary: a failure to retrieve an existing value is not evidence that the value is absent from the source.

### 4.2 Experimental conditions

Three conditions will be compared while keeping the database snapshot, user permissions, model, prompt, embedding model, retrieval configuration, and entity-resolution safeguards consistent.

**System A — Baseline RAG.** The agent resolves a student entity, checks authorization, retrieves evidence scoped to the resolved student identifier, and generates a response using the retrieved context. It does not apply the experimental post-generation evidence verifier.

**System B — RAG with evidence verification.** This condition adds a deterministic post-generation check. The verifier identifies the recognized field requested by the user, extracts that field's value from retrieved evidence, and checks whether the generated answer contains that value. If the answer cannot be verified, the agent abstains. The verifier is intentionally narrow and will not be described as a general-purpose fact checker.

**System C — Evidence verification with source-aware selective decisions.** This condition includes System B and adds a pre-generation check of source-field availability. For a recognized field, it checks whether the structured database contains a non-empty value or a related record. If the value is genuinely absent, the agent abstains before calling the LLM. If the source contains the value but retrieval does not provide usable evidence, this is recorded as a retrieval/evidence failure rather than a missing-source case. The availability check returns only a status and reason, not the student's field value.

Entity ambiguity clarification and access-control checks will be retained in all conditions as common safeguards. The experiment will therefore not attribute clarification improvements to System C. The planned comparisons isolate the effect of post-generation evidence verification (A versus B), the additional source-aware selective decision gate (B versus C), and the combined intervention (A versus C).

### 4.3 Repeated runs and evaluation metrics

Each query will be executed five times per condition. With 200 queries and three systems, this produces up to 3,000 attempts. The experiment runner will preserve the run number, system, case identifier, observable decision, generated answer, latency, model configuration, and operational errors. Condition order will be rotated between repeated runs to reduce fixed-order effects. Failed API or infrastructure calls will be reported as operational failures and will not be counted as abstentions.

The evaluation will include exact answer accuracy, answer coverage, correct-answer rate over all answerable cases, decision accuracy, clarification precision and recall, missing-information abstention precision and recall, and median response latency. Exact-match scoring will be supplemented by manual review of semantically equivalent answers. Evidence support will be assessed separately because correctness and grounding are related but different properties.

The query will be the unit of statistical analysis. Repeated outputs for a query will be aggregated within that query before system comparisons. Paired, category-stratified bootstrap confidence intervals will be used to estimate differences between systems. This avoids treating repeated attempts of the same question as independent samples.

### 4.4 Human validation

A stratified sample of 40 unique queries will be selected: 20 answerable, 10 ambiguous, and 10 source-missing. Two reviewers will independently annotate all five runs for all three systems, giving up to 600 output-level reviews. The rubric will cover action appropriateness, answer correctness, evidence support, evidence sufficiency, and unsupported factual claims. Cohen's kappa and raw agreement will be reported for independent categorical annotations. Because the sample is limited, this human validation will be considered exploratory and its limitations will be stated.

## 5. Expected contribution

The expected contribution is a practical, reproducible framework for evaluating observable accuracy and trustworthiness outcomes in a retrieval-augmented agent. The work will distinguish a correct answer from an evidence-supported answer, and source-level missing information from retrieval failure. It will provide empirical evidence about whether a deterministic verifier and a source-aware decision gate improve reliability, and what trade-offs they introduce.

The work is deliberately scoped as an initial controlled study, not as a universal benchmark for all autonomous agents. Its structured database setting makes it possible to establish source-grounded reference labels and inspect the actual database state. This provides a transparent foundation for later research on multi-step tool-using agents, knowledge graphs, more complex workflows, and multilingual question answering. Urdu and Pashto evaluation is a possible future direction motivated by my undergraduate project, but it will not be a core experimental variable in the initial study.

## 6. Proposed research schedule

In the first stage, I will strengthen my knowledge of artificial intelligence, information retrieval, machine learning, databases, research design, and statistical evaluation. I will conduct a focused literature review on RAG evaluation, evidence attribution, selective question answering, and trustworthy AI, and refine the research scope with Professor Xie.

In the second stage, I will validate the synthetic benchmark against a frozen database snapshot, finalize the system definitions, implement and test the three conditions, and conduct a small pilot. The pilot will be used to verify the experimental controls and improve the human-review rubric. After the pilot, I will run the repeated experiments, preserve the raw outputs, and analyze the results at the query level.

In the final stage, I will complete the human validation, interpret the results, document limitations, and write the master's thesis. If the findings are sufficiently rigorous and novel, I will prepare a paper for submission to a relevant conference or journal. The detailed timeline will be adapted to DMU's master's programme structure and the guidance of my supervisor.

## 7. Preparation and suitability

My bachelor's degree provided training in programming, data structures and algorithms, object-oriented programming, database management systems, software engineering, and artificial intelligence-related subjects. My final-year project gave me practical experience implementing a RAG-based information system, but I recognize that a research degree requires stronger experimental design, critical reading, statistical reasoning, and scientific writing. I intend to develop these skills through graduate coursework and supervised research.

I am motivated by Professor Xie's suggested research direction because it connects directly to a problem I encountered while building a generative AI application: how can we know whether an agent's answer is not only plausible, but correct and supported by reliable evidence? I would welcome the opportunity to refine this proposal with his guidance and align it with the research priorities and facilities of Dalian Maritime University.

## References

1. Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems*.
2. Es, S. et al. (2024). RAGAS: Automated Evaluation of Retrieval Augmented Generation. *Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations*.
3. Saad-Falcon, J. et al. (2024). ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. *Proceedings of NAACL-HLT*.
4. Kamath, A. et al. (2020). Selective Question Answering under Domain Shift.
