# AEOBrand: A Framework for Measuring Brand Visibility in Generative Answer Engines
## Literature Survey

**Project area:** Answer Engine Optimization, generative information retrieval, and LLM evaluation  
**Document type:** Graduate project literature survey  
**Institution:** [Institution / University]  
**Department:** [Department]  
**Programme:** [M.Tech / Ph.D. / Other]  
**Submitted by:** [Team member names and roll numbers]  
**Guide:** [Guide name and designation]  
**Date:** October 2026

> **Submission note.** This survey reviews 12 research papers individually. The team should replace the cover-page fields and verify the required paper count with its faculty. If a four-member team is expected to submit 30–40 papers, this 12-paper edition is a substantial starting draft, not a substitute for that larger requirement. Add papers that the team has personally read and extend each individual review before submission.

## Abstract

Generative answer engines change how people discover products and organizations. Rather than returning only ranked links, these systems may synthesize information from model parameters, retrieved documents, and web sources. For a brand, visibility therefore depends not only on conventional search rank but also on whether the entity is retrieved, named, described accurately, and supported by sources in an answer. This survey examines twelve studies spanning dense retrieval, retrieval-augmented generation (RAG), browser-assisted answering, citation-grounded generation, factuality measurement, automated RAG evaluation, LLM-based judging, and generative engine optimization (GEO). Each paper is reviewed individually, followed by a synthesis of the methods and unresolved measurement issues relevant to AEOBrand, a prototype intended to collect prompts and model responses and report brand-mention and citation indicators. The review finds that the project’s measurement problem is timely, but that valid conclusions require controlled query sampling, repeated observations, cross-model testing, auditable citation checks, and human-validated extraction. The proposed BVI, CMCS, and CAS are treated here as prototype operational metrics, not established or validated scientific measures.

**Index Terms—** Answer Engine Optimization, generative engine optimization, large language models, information retrieval, retrieval-augmented generation, citations, evaluation.

## 1. Introduction

Search interfaces are shifting from lists of documents toward conversational answers that summarize or synthesize information. This shift changes the unit of visibility. In a conventional search setting, an organization may track a page’s position for a query. In a generative answer, the organization may be absent, named without a source, compared with competitors, or represented through third-party material. The answer can also vary with wording, model version, retrieval conditions, and time. A single ranking or one successful demonstration is consequently an inadequate description of exposure.

The emerging literature uses **Generative Engine Optimization (GEO)** for methods intended to improve content visibility in generative-engine responses [5]. **Answer Engine Optimization (AEO)** is used more broadly in practice for work aimed at being represented in direct answers. The terminology is still developing; this survey uses AEO for the project’s measurement objective and GEO when discussing the research framework introduced by Aggarwal et al. [5]. The distinction matters: measuring visibility is not the same as proving that an optimization intervention caused it.

AEOBrand is a Python prototype organized around configuration, prompt synthesis and validation, model dispatch, response evaluation, scoring, JSON reports, and a browser dashboard. Its data model captures brand, competitors, keywords, context, prompt intent, model response, extracted mentions, sentiment, and citations. The intended contribution is an experiment and monitoring workflow, rather than a new language model or a validated theory of brand authority. The architecture anticipates multiple providers, while the implementation documentation also identifies simulated runs and a currently limited provider set. Results from simulated responses must not be interpreted as measurements of real model behavior.

This review addresses three questions: (1) what methods underpin retrieval and source-grounded answers; (2) how should generated answers, citations, and evaluators be assessed; and (3) what research gap remains for repeatable, cross-model measurement of entity visibility? The paper summaries below distinguish each study’s contribution from its limitations and relevance to AEOBrand.

## 2. Review Method and Scope

The selection is a focused, narrative review of twelve primary studies and surveys identified through scholarly search using combinations of *generative engine optimization*, *retrieval-augmented generation*, *dense passage retrieval*, *answer citations*, *LLM evaluation*, and *factuality*. Canonical arXiv records and the publication details reported on those records were used to identify papers and stable links. The papers were selected for direct relevance to one or more pipeline stages: retrieval, generation, citation, measurement, or evaluator reliability. This is not a PRISMA systematic review: no exhaustive database search, independent screening, or formal risk-of-bias assessment was conducted. Authors should verify the final citations and consult full papers before submission.

The synthesis favors research studies over commercial AEO advice. It does not claim that the reviewed papers validate AEOBrand’s particular formulas. “Visibility,” “citation support,” and “citation authority” are separate constructs and should not be conflated.

## 3. Individual Literature Review

### 3.1 Dense Passage Retrieval for Open-Domain Question Answering

Karpukhin et al. [1] introduce Dense Passage Retrieval (DPR), a dual-encoder approach that embeds questions and passages into a shared vector space and retrieves candidate passages by semantic similarity. Evaluations on open-domain question-answering datasets showed that the learned retriever could outperform a strong BM25 baseline on top-20 passage retrieval accuracy and support improved end-to-end question answering. The key contribution for this project is the demonstration that retrieval is a measurable stage in an answer pipeline: evidence may be unavailable to a generator because it was not retrieved in the first place. DPR does not study brands or generative answer visibility, and retrieval accuracy does not establish that a final answer mentions an entity. For AEOBrand, it motivates recording query context and retrieved evidence where accessible, instead of treating generated text as an unexplained outcome.

### 3.2 Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

Lewis et al. [2] propose RAG, combining a pretrained sequence-to-sequence generator with a non-parametric dense index of Wikipedia accessed through a neural retriever. The study compares formulations that condition generation on retrieved passages at sequence or token level and reports strong results on knowledge-intensive tasks, including open-domain question answering. The work is foundational because it makes explicit that generated answers may depend on both model parameters and external documents; this provides a conceptual basis for tracking citations and sources. It does not define brand visibility or establish a universal relationship between a source’s authority and an entity’s mention. AEOBrand’s citation metrics should therefore distinguish source presence from source quality and verify whether cited material actually supports the statement about the brand.

### 3.3 REALM: Retrieval-Augmented Language Model Pre-Training

Guu et al. [3] introduce REALM, integrating a latent knowledge retriever into language-model pretraining and enabling retrieval over a large document collection during training and inference. On three open-domain question-answering benchmarks, the authors report absolute accuracy improvements of 4–16 percentage points over the compared approaches, alongside interpretability and modularity benefits. REALM is important to this survey because it positions retrieval not merely as a bolt-on generation component but as part of how a model accesses external knowledge. The study is not concerned with public-facing brand representation, and benchmark QA accuracy cannot be transferred directly to visibility scores. For AEOBrand, the paper reinforces the need to treat external knowledge access as a possible determinant of an answer and to avoid assuming that model parameters alone explain the response.

### 3.4 WebGPT: Browser-Assisted Question-Answering with Human Feedback

Nakano et al. [4] train a model to answer long-form questions through a text-based browser environment. The system learns to search and navigate web pages and is optimized using demonstrations and a reward model trained on human preferences. The authors also emphasize collecting references while browsing, making answer evaluation more inspectable. Human evaluators preferred the best WebGPT model to the human demonstrators in 56% of comparisons and to highly rated Reddit answers in 69% in the reported setting. These findings show that source-seeking behavior can be integrated into answer generation, but the result is tied to a particular dataset, interface, and evaluation protocol. For AEOBrand, this paper motivates treating citations as observable evidence and separately evaluating answer quality; it does not justify using raw citation counts as a measure of authority.

### 3.4 Teaching Language Models to Support Answers with Verified Quotes

Menick et al. [5] investigate GopherCite, an “open-book” question-answering model trained to provide supporting quotations and to abstain when uncertain. Human evaluation on subsets of Natural Questions and ELI5 found high-quality answers in 80% and 67% of cases, respectively; abstention on questions with lower confidence improved those rates in the reported experiments. The study illustrates two useful principles for AEO measurement: an answer can expose evidence for claims, and uncertainty or non-response is meaningful rather than a system failure. At the same time, a citation alone does not guarantee a true claim, a limitation the authors also test on TruthfulQA. AEOBrand should record whether the source is merely listed or whether it supports the exact brand-related assertion, and should retain an “uncertain/insufficient evidence” outcome for automated extraction.

### 3.5 GEO: Generative Engine Optimization

Aggarwal et al. [6] formalize Generative Engine Optimization and introduce GEO-bench, a benchmark of queries and relevant sources for evaluating content visibility in generative-engine responses. Their experiments study content optimization strategies and report visibility improvements of up to 40% in the evaluated settings, with variation across domains. This is the closest paper to AEOBrand’s application: it frames creator visibility as an outcome that can be measured under black-box generative systems. The reported gains should not be generalized to all engines, industries, or current models; benchmark design and engine behavior constrain the result. GEO focuses on optimizing content, whereas AEOBrand’s stated emphasis is monitoring brand representation. The distinction suggests a future controlled experiment: compare baseline and modified content under matched prompts and engine conditions rather than inferring causality from observational scores.

### 3.6 Retrieval-Augmented Generation for Large Language Models: A Survey

Gao et al. [7] survey RAG methods and organize them into Naive, Advanced, and Modular paradigms, examining retrieval, generation, augmentation, evaluation, and open challenges. The survey is useful for placing AEOBrand’s response pipeline in a broader system context: changes in retrieval and context preparation can affect downstream answers, independently of the generator itself. It also emphasizes recurring problems such as stale knowledge, hallucinations, and limited transparency. As a survey, it synthesizes methods rather than providing a controlled experiment on brand mentions. For this project, the important implication is architectural: a score based only on final text cannot identify whether visibility changes came from the retriever, source corpus, prompt, or model. Whenever possible, AEOBrand should capture provider, model/version, run time, prompt, and available retrieval/source metadata.

### 3.7 Enabling Large Language Models to Generate Text with Citations

Gao et al. [8] present ALCE, a benchmark for evaluating answers with citations across dimensions including fluency, correctness, and citation quality. The benchmark requires end-to-end retrieval and answer generation and compares automatic measures with human judgments. Experiments show that contemporary systems can produce fluent responses while leaving substantial portions of claims without complete citation support; the authors report that even the best models on ELI5 lack complete citation support about half the time. This work provides a direct methodological warning for AEOBrand: counting URLs or source names is not equivalent to checking citation completeness or correctness. ALCE’s task is answer-level citation quality, not brand visibility. It nevertheless suggests that project evaluation should annotate claim-to-source support and report citation precision and coverage separately from domain counts.

### 3.8 FActScore: Fine-Grained Atomic Evaluation of Factual Precision in Long Form Text Generation

Min et al. [9] propose FActScore, which decomposes long-form output into atomic facts and estimates the percentage supported by a reliable knowledge source. They argue that binary judgments are too coarse because an answer can contain both accurate and unsupported claims. Human judgments and an automated retrieval-plus-language-model estimator are used to evaluate generated biographies and model outputs. The paper is relevant because brand descriptions can contain multiple claims—product capabilities, market position, pricing, or comparisons—whose correctness may differ within one response. A single sentiment label or “brand mentioned” boolean cannot represent those differences. FActScore is not a brand-metric proposal and its evidence source and domain assumptions matter. AEOBrand could borrow the atomic-claim principle for a later factuality module, with human-reviewed claim/source annotations.

### 3.9 Ragas: Automated Evaluation of Retrieval-Augmented Generation

Es et al. [10] introduce Ragas, a reference-free framework for evaluating RAG systems across retrieval relevance, faithfulness to provided context, and response quality. Its motivation is practical: RAG pipelines have multiple components, and requiring human ground truth for every iteration slows development. The framework offers an evaluation vocabulary that can help separate evidence retrieval from answer generation. It is not designed to measure brand prominence or whether a citation has commercial authority. Automated, reference-free measures can also inherit errors from the language model used as an evaluator. AEOBrand’s pipeline similarly uses model-based extraction in live mode, so this study supports tracking evaluator configuration and validating extracted labels against human annotation rather than treating automated scores as ground truth.

### 3.10 Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena

Zheng et al. [11] examine strong LLMs as evaluators for open-ended assistant responses and introduce MT-Bench and Chatbot Arena as complementary evaluation resources. Their analysis identifies position, verbosity, and self-enhancement biases, while reporting substantial agreement between GPT-4 judgments and human preferences in their tested conditions. The paper supports using LLM evaluators to scale structured assessment, but also makes clear that the judge is not neutral simply because it returns valid JSON. In AEOBrand, a judge that sees the target brand and a list of competitors may make extraction mistakes or favor particular wording. A robust evaluation should include blind or rule-based cross-checks, a human-labeled sample, inter-annotator agreement, and sensitivity analysis across judge models and prompt versions.

### 3.11 Lost in the Middle: How Language Models Use Long Contexts

Liu et al. [12] study how language models use information placed at different positions in long input contexts. Across multi-document question answering and key-value retrieval, they find that performance can be higher when relevant information is at the beginning or end and can decline when it is positioned in the middle. This “lost in the middle” effect is relevant when answer engines synthesize many sources: source order and context length may influence which evidence is used or surfaced. The paper does not investigate brand content, ranking, or citation authority. It does, however, undermine the assumption that adding more brand-related material to a context will monotonically improve representation. An AEOBrand experiment should log prompt length and, when observable, evidence position or source ordering, and should test prompt variants instead of interpreting one response as stable behavior.

### 3.12 The GEO Study as a Measurement Foundation: Benchmarking and Domain Variation

GEO-bench in [6] illustrates why benchmark construction is central to turning the project from a dashboard into an empirical instrument. It provides a systematic query set and tests visibility changes across domains; the work reports that optimization strategies do not transfer uniformly. This reinforces the need for domain-aware prompt sampling and fixed evaluation sets. However, the study’s benchmark and engine snapshots represent a defined experimental setting, while commercial answer engines and retrieval policies change over time. AEOBrand’s synthetic prompts may improve breadth but are not a substitute for a documented sample frame. The project should retain a stable “panel” of prompts for longitudinal comparisons, separately label newly generated exploratory prompts, and publish the provider/model, dates, prompt construction process, and exclusion rules.

## 4. Comparative Synthesis and Research Gap

Across the reviewed work, answer visibility is the endpoint of a chain rather than a single model property. DPR and RAG [1], [2] show how retrieval determines the evidence available to generation. Browser-assisted systems and citation-grounded generation [3], [4], [7] make sources more inspectable, while also showing that citations require their own evaluation. FActScore and Ragas [8], [9] decompose output quality into measurable dimensions. LLM-as-a-judge research [10] offers scalable annotation but documents systematic bias. GEO [5] supplies the clearest experimental framing for content visibility; the RAG survey and long-context study [6], [11] explain why retrieval configuration and context position matter.

A research gap remains between controlled generative-engine visibility experiments and lightweight operational dashboards. Existing work does not establish a universally accepted brand visibility index, a standard cross-model consistency formula, or a scalar citation-authority measure. These constructs require definitions, calibration, and evidence of reliability and validity. AEOBrand can contribute a transparent prototype and evaluation protocol, provided it avoids presenting prototype scores as established measures.

### 4.1 Measurement risks in the current prototype

1. **Prompt sampling and leakage:** If prompts name the target brand, the system tests response to explicit prompting, not unaided discovery. Brand-seeded and brand-neutral prompts should be analyzed as separate strata.
2. **Model and time dependence:** Results should include provider, model identifier/version, run date, region, sampling parameters, and error rate. Repeat calls are needed because outputs can vary.
3. **Simulated runs:** Template or mock responses are useful for software tests only. They are not evidence of external model visibility.
4. **Judge reliability:** LLM-extracted mentions, sentiment, and citations need a human-labeled validation set, clear annotation rules, precision/recall, and disagreement reporting.
5. **Citation semantics:** A unique domain count is not an authority score. Authority requires a declared rubric or external source-quality evidence; support requires claim-level verification.
6. **Metric definition:** The project’s documented CMCS uses prompt-level mention-count variation even though its name implies cross-model consistency. Until multiple models are evaluated on matched prompts, label it prompt-level consistency. A sample-standard-deviation penalty is sensitive to prompt count and scale.
7. **Denominators and aggregation:** Failed calls, duplicate domains, and multiple citations in one answer affect the denominator. Formula, normalization, missing-data policy, and confidence intervals must be specified before comparisons.
8. **Causal claims:** A score increase after a content change does not establish that the change caused it unless prompts, model conditions, and sampling are controlled.

### 4.2 Proposed operational definitions for validation

The current codebase implements prototype formulas, and these definitions are not validated by the cited papers. For experimental reporting, a transparent starting point is:

- **Brand mention rate:** successful responses with an explicitly defined brand/entity mention divided by successful responses, reported with numerator and denominator.
- **Cross-model consistency:** agreement in a binary mention outcome across model providers for the *same* prompts, with a named agreement statistic and uncertainty interval. Do not call prompt-level variation cross-model consistency.
- **Citation coverage:** brand-related factual claims supported by at least one verifiable cited source divided by all sampled brand-related claims.
- **Citation authority:** a separate score using a published, reproducible source-quality rubric; do not infer authority from the number of unique domains.
- **Sentiment:** report the class distribution and human-validated classifier performance; sentiment is not a substitute for factual accuracy.

These proposals should be preregistered or documented before the evaluation and revised only with a versioned metric specification.

## 5. Proposed Research Method for AEOBrand

A defensible evaluation can be conducted in five stages. First, define the unit of analysis (one prompt–provider–model–time response) and build a query panel across informational, comparative, transactional, problem-aware, feature-aware, and alternative-seeking intents. Separate prompts that explicitly contain the brand from brand-neutral discovery queries. Second, submit the same prompt panel to each available provider under recorded model settings, with repeated runs and a fixed observation window. Third, preserve raw responses and source metadata, then annotate entity identity, mention prominence, factual claims, sentiment, competitors, and citations using a written codebook. Fourth, compare automatic extraction against a stratified, independently double-annotated sample; publish per-label precision, recall, and agreement. Finally, report mention rates with uncertainty intervals, model-specific results, citation support/coverage, failures, and changes over time. The dashboard should display the run mode and denominator prominently.

A minimal baseline should compare lexical/entity matching against the LLM judge, and compare the project’s synthetic prompts with a fixed manually reviewed panel. Ablations can test the effects of brand inclusion, intent class, prompt paraphrase, region, and time. The primary outcome should be specified before analysis; secondary measures should not be selected after seeing the results. This design helps distinguish software correctness from evidence about generative engines.

## 6. Alignment with the AEOBrand Project

The reviewed research maps to the project architecture as follows:

- **Configuration and prompt synthesis:** the brand, competitor, geography, use-case, and intent fields define the sampling frame. Prompt validation can reduce duplicates, but diversity scores should be reported as a prompt-set property rather than evidence of representativeness.
- **Dispatch and response capture:** multi-provider dispatch is necessary for cross-model claims. Provider/model identifiers, timestamps, failures, and request settings must be retained for reproducibility.
- **Response evaluation:** entity extraction and sentiment are annotation tasks. The LLM-as-a-judge design should be backed by labeled examples and audit trails.
- **Scoring:** BVI, CMCS, and CAS are local project names and provisional formulas. The current CAS unique-domain count does not measure source authority; current CMCS implementation measures variation across prompts and is not cross-model without model grouping.
- **Reporting:** JSON run records and a dashboard support inspection and longitudinal comparisons, provided simulated and live outcomes are clearly separated and only live observations are used to make empirical claims.

Figure 1 presents the intended measurement workflow. Its multi-provider and longitudinal elements are research extensions and should not be read as evidence that those capabilities have been fully implemented.

{FIGURE_PIPELINE}

**Figure 1.** AEOBrand measurement workflow and validation boundary. **Source:** Authors’ illustration based on the AEOBrand project architecture and the literature reviewed in [1]–[12]; future/optional components are marked as such.

## 7. Conclusion

The literature supports a careful study of how organizations are represented in generated answers, but it does not justify treating mentions, citations, or sentiment as self-validating measures. Retrieval, generation, citation behavior, and evaluation are interdependent. GEO provides an initial experimental model for visibility optimization, while work on RAG, grounded answers, factuality, and evaluator bias supplies methods and cautions that a monitoring system must address.

AEOBrand’s strongest graduate-project contribution is therefore a transparent and reproducible evaluation workflow: a documented prompt panel, repeated and matched provider calls, retained raw evidence, validated extraction, and clearly defined outcomes. Until such validation is completed, BVI, CMCS, and CAS should be presented as prototype indicators. Simulated responses can verify pipeline mechanics, but only controlled observations from real engines can support claims about brand visibility.

## References

[1] V. Karpukhin, B. Oğuz, S. Min, P. Lewis, L. Wu, S. Edunov, D. Chen, and W.-T. Yih, “Dense Passage Retrieval for Open-Domain Question Answering,” in *Proceedings of EMNLP*, 2020, pp. 6769–6781. doi: 10.18653/v1/2020.emnlp-main.550. Available: https://aclanthology.org/2020.emnlp-main.550/

[2] P. Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, 2020. Available: https://arxiv.org/abs/2005.11401

[3] K. Guu, K. Lee, Z. Tung, P. Pasupat, and M.-W. Chang, “REALM: Retrieval-Augmented Language Model Pre-Training,” in *Proceedings of the 37th International Conference on Machine Learning (ICML)*, PMLR, vol. 119, pp. 3929–3938, 2020. Available: https://arxiv.org/abs/2002.08909

[4] R. Nakano et al., “WebGPT: Browser-assisted Question-Answering with Human Feedback,” arXiv:2112.09332, 2021. Available: https://arxiv.org/abs/2112.09332

[5] J. Menick et al., “Teaching Language Models to Support Answers with Verified Quotes,” arXiv:2203.11147, 2022. Available: https://arxiv.org/abs/2203.11147

[6] P. Aggarwal et al., “GEO: Generative Engine Optimization,” in *Proceedings of the 30th ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD)*, 2024. doi: 10.1145/3637528.3671900. Preprint: https://arxiv.org/abs/2311.09735

[7] Y. Gao et al., “Retrieval-Augmented Generation for Large Language Models: A Survey,” arXiv:2312.10997, 2023 (revised 2024). Available: https://arxiv.org/abs/2312.10997

[8] T. Gao, H. Yen, J. Yu, and D. Chen, “Enabling Large Language Models to Generate Text with Citations,” in *Proceedings of EMNLP*, 2023. Available: https://arxiv.org/abs/2305.14627

[9] S. Min et al., “FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation,” in *Proceedings of EMNLP*, 2023. Available: https://arxiv.org/abs/2305.14251

[10] S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, “RAGAS: Automated Evaluation of Retrieval Augmented Generation,” in *Proceedings of EACL*, 2024. Available: https://arxiv.org/abs/2309.15217

[11] L. Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena,” in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 36, 2023. Available: https://arxiv.org/abs/2306.05685

[12] N. F. Liu et al., “Lost in the Middle: How Language Models Use Long Contexts,” *Transactions of the Association for Computational Linguistics*, vol. 12, pp. 157–173, 2024. doi: 10.1162/tacl_a_00638. Available: https://arxiv.org/abs/2307.03172

## Citation and Originality Statement

This document is an original synthesis of the cited research, not a reproduction of their text. The authors should check every source against the full paper, revise the analysis in their own understanding, complete the institutional and authorship fields, and follow their institution’s rules for AI-assisted writing and disclosure. No tool or drafting process can guarantee a particular similarity percentage. A similarity score below 10% cannot be promised without the institution’s specified checker and its comparison corpus; quotations, references, and common technical phrases may be treated differently by different systems. Cite all reused ideas, figures, and data, and do not submit unverified claims as original findings.
