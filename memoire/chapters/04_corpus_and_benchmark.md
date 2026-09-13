# Chapter 4 — Corpus and Benchmark Construction

## 4.1 Objective

The experimental corpus must support two requirements that are often in tension in legal question answering. Retrieval requires units small enough to isolate the relevant rule, while answer generation requires enough hierarchy to interpret that rule correctly. The project therefore represents each source at two linked levels: legal parents and retrievable children.

This redesign was necessary before interpreting retrieval failures as limitations of RAG. The historical corpus used 132 comparatively flat chunks, some exceeding 30,000 characters. The historical generator then received only the first 1,500 characters of each retrieved chunk. As a result, a chunk could count as retrieved even when the supporting paragraph was omitted from the generation context.

## 4.2 Regulatory sources and identity

The E1 corpus is constructed from the project's stored EASA Easy Access Rules source export. The parser preserves the identity of each underlying regulation rather than treating the combined publication as one undifferentiated document.

Every parent records:

- document and regulation identity;
- regulation type and version;
- formal title;
- document type, such as ARTICLE, ANNEX, RECITALS, or GM;
- hierarchy path and parent title;
- canonical citation;
- cross-references;
- source XML range;
- ordered child identifiers.

This identity layer prevents articles with the same number in different regulations from colliding. It also preserves the distinction between binding regulation text and guidance material.

TODO literature: cite the exact EASA Easy Access Rules edition and official source URL.

## 4.3 Parent–child representation

A parent is a coherent legal unit such as a complete article, annex, recitals block, or guidance section. A child is an atomic retrievable unit such as a paragraph, list item, table row, table header, or callout.

Each child stores:

- a stable child and parent identifier;
- canonical citation;
- sequence within the parent;
- marker path;
- unit type;
- evidence text;
- retrieval text enriched with document and hierarchy metadata;
- word and character counts;
- source location.

Tables are represented at row level. Table headers and governing text are repeated where necessary so that a row remains interpretable after retrieval. Short legal units are not merged merely to satisfy a generic minimum size: an atomic item can be meaningful when its hierarchy and governing text are preserved.

The validated E1 corpus contains:

| Unit | Count |
|---|---:|
| Legal parents | 109 |
| Retrievable children | 1,535 |
| ARTICLE parents | 36 |
| ANNEX parents | 10 |
| RECITALS parents | 4 |
| GM parents | 59 |

Child types include 823 list items, 477 paragraphs, 105 table rows, 8 table headers, and 122 callouts.

## 4.4 Structural validation

The corpus build is deterministic and validated through automated and manual checks. The validation stage checks identifier uniqueness, parent-child lineage, legal-type consistency, source ranges, citation fields, table context, and sequence ordering.

The promoted E1 output reported zero critical issues and zero warnings. Its principal hashes are:

- parents.jsonl: 4E481936003E209DA32718998C15099C04652FEF5B260C7546A37495C43AC9E0;
- children.jsonl: 7860E9C1870CC752F357A7E174E027A1DC01BA297ACB4D82DC1BB48E9E7DF745.

These hashes are inherited by downstream retrieval and context manifests.

## 4.5 Legacy benchmark lineage

The historical dataset contains 300 synthetic question-answer records derived from the flat corpus. To preserve continuity without silently treating the old source field as exact evidence, every record was mapped to the E1 hierarchy.

The parent-lineage audit produced:

| Disposition | Count |
|---|---:|
| Automatically mapped | 291 |
| Manually accepted | 4 |
| Excluded as invalid | 4 |
| Rewrite required | 1 |

Fuzzy similarity alone was never accepted as gold evidence. Ambiguous mappings were placed in a review queue and resolved explicitly.

## 4.6 Candidate evidence audit

The 100 question IDs shared by the historical few-shot, RAG, and LoRA outputs were then audited against exact E1 children.

The AI-assisted audit produced:

| Decision | Count |
|---|---:|
| Retained without text change | 78 |
| Rewritten and evidence-linked | 21 |
| Excluded as invalid | 1 |

QA_0003 was excluded because its source was table-of-contents text and its answer merely redirected the reader to a section instead of answering from regulatory evidence.

The retained candidate benchmark contains 99 records. Every retained record has a document-qualified parent and at least one selected child evidence identifier. The audit corrected issues such as incorrect regulation attribution, incomplete paragraph citations, unsupported consequences, and answers that converted listed occurrences into prohibitions.

This remains an AI-assisted candidate benchmark. The same system that proposed corrections cannot independently certify them.

## 4.7 Independent-review protocol

The independent-review package contains 33 unique records:

- all 22 corrected or excluded exception records;
- the three deepest hybrid retrieval residuals;
- ten deterministic unchanged controls stratified by source type and split.

The reviewer records whether the question is unambiguous, the answer is fully supported, the citation is correct, and the selected evidence set is complete. Alternative acceptable child IDs can be added when equivalent legal wording appears in more than one source unit.

This last point matters for exact-child evaluation. In QA_0080, equivalent annex wording appears outside the originally selected child. A retrieval system may therefore be substantively correct while exact-child scoring calls it a miss. The reviewed benchmark must support multiple acceptable evidence sets where the legal text justifies them.

At the time of this draft, the 33-row review is not complete. All benchmark-dependent percentages in later chapters remain candidate results.

## 4.8 Grouped development and test split

Question-level random splitting would leak highly similar evidence when several questions originate from the same article or guidance section. The candidate benchmark is therefore split by legal parent.

| Split | Questions | Parent groups |
|---|---:|---:|
| Development | 42 | 12 |
| Test | 57 | 48 |

No parent appears in both partitions. The deterministic seed is aviation-rag-legacy100-v1.

Model selection and configuration choices use development data. The held-out test view is reported only after selection. Because candidate test results have now been opened, later tuning must remain development-only or use a newly frozen confirmation set.

## 4.9 Validity limitations

The benchmark has four principal limitations.

First, its questions and original answers are synthetic and may inherit the style and assumptions of the generating model. Second, the evidence audit is AI-assisted pending independent review. Third, exact-child scoring may undercount alternative but equivalent legal evidence. Fourth, the sample contains relatively few cross-reference and multi-document questions, limiting conclusions about agentic retrieval.

These limitations do not invalidate the benchmark as a development instrument. They determine which claims can be made from it. Candidate results may guide architecture and failure analysis, while final accuracy and ceiling claims require the reviewed gold version.

## 4.10 Reproducibility artifacts

The corpus audit, legacy mapping audit, candidate benchmark, split manifest, review queue, and input hashes are stored under versioned project directories. Original historical files are preserved unchanged.

Primary artifacts:

- data/processed/E1_parent_child_v1;
- data/evaluation/legacy_to_e1_v1;
- data/evaluation/legacy100_ai_audited_v1;
- data/evaluation/legacy100_candidate_splits_v1;
- data/evaluation/independent_review_v1;
- reports/E1_corpus_audit.md;
- reports/legacy100_ai_audit.md.

The final gold build will receive a new version and manifest rather than overwriting the candidate benchmark.
