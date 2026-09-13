# E1 Parent-Child Corpus Audit

**Audit date:** 17 July 2026  
**Schema:** parent_child_v1  
**Source snapshot:** EASA Easy Access Rules for Occurrence Reporting XML export dated 27 September 2023  
**Source SHA-256:** 716FBFA41E7D934A9B93E67C733232AB8A9DC7E889D12D724D7D0110D0BA235C  
**Decision:** Accepted as the structural corpus for E1 retrieval work.

## Purpose

E1 isolates the effect of hierarchy-aware parent-child parsing from the later embedding, hybrid-retrieval, reranking, and generation changes. It replaces the historical 132 flat chunks, which mixed document identities, lost table context, and truncated content.

## Output inventory

| Record set | Count | SHA-256 |
|---|---:|---|
| parents.jsonl | 109 | 4E481936003E209DA32718998C15099C04652FEF5B260C7546A37495C43AC9E0 |
| children.jsonl | 1,535 | 7860E9C1870CC752F357A7E174E027A1DC01BA297ACB4D82DC1BB48E9E7DF745 |
| validation.json | 1 report | E83E22346F51928B152FC2D6AC4BDDD0B5A1FC20CEA0CE30A5E57FE90A5458E5 |

The versioned build manifest also records Python, platform, timestamps, source path, document version, source hash, and output hashes.

## Structural results

### Parents by document

| Document | Parents |
|---|---:|
| Regulation (EU) No 376/2014 | 28 |
| Implementing Regulation (EU) 2015/1018 | 8 |
| Delegated Regulation (EU) 2020/2034 | 6 |
| Implementing Regulation (EU) 2021/2082 | 8 |
| Guidance material for Regulation (EU) No 376/2014 | 59 |

### Parents by legal unit

| Type | Parents |
|---|---:|
| ARTICLE | 36 |
| ANNEX | 10 |
| RECITALS | 4 |
| GM | 59 |

### Children by evidence unit

| Type | Children |
|---|---:|
| Paragraph | 477 |
| List item | 823 |
| Table row | 105 |
| Table header | 8 |
| Callout/layout table | 122 |

Child length ranges from 2 to 1,615 characters, with a mean of 192.61. There are 87 short units below 20 characters and 8 units above 1,000 characters. The short units are retained because they are principally legal list labels or table values whose meaning is restored by citation, hierarchy, headers, and governing text in retrieval_text.

## Automated acceptance checks

- 12 parser and integrity tests pass.
- Zero critical validation issues and zero warnings.
- Parent IDs and child IDs are unique.
- Every child points to an existing parent.
- Every parent contains at least one child.
- All four regulations retain their recitals.
- Duplicate article numbers across regulations have distinct document-qualified IDs.
- Guidance sentences mentioning an article do not create false ARTICLE parents.
- Article paragraph paths retain nested citations such as Article 4(1)(a)(i).
- The numbered and unnumbered annex patterns use short canonical IDs.
- The final acronym reference table has its own GM parent and is not attached to section 5.10.
- Table rows retain column headers and vertically merged governing cells.
- A second independent build produced identical parent, child, and validation bytes.

## Manual stratified review

The following parents were inspected across the beginning, middle, and end of each legal-unit stratum:

| Stratum | Reviewed parent IDs |
|---|---|
| RECITALS | EU_376_2014_RECITALS; EU_2020_2034_RECITALS; EU_2021_2082_RECITALS |
| ARTICLE | EU_376_2014_ART_1; EU_376_2014_ART_19; EU_2021_2082_ART_6 |
| ANNEX | EU_376_2014_ANNEX_I; EU_2015_1018_ANNEX_III; EU_2021_2082_ANNEX |
| GM | GM_EU_376_2014_SEC_1_1; GM_EU_376_2014_SEC_3_8; GM_EU_376_2014_SEC_5_10 |

Checks covered document identity, parent boundary, title, canonical citation, first/last child order, source anchors, and binding-versus-guidance separation. No blocking discrepancy was found.

Targeted checks also confirmed:

- the complete Article 4 nested sequence is represented without the earlier Article 4(1)(i)(ii) path error;
- Regulations 2020/2034 and 2021/2082 receive implicit recitals parents even though the source styles omit an explicit recitals heading;
- ERCS severity rows repeat the vertically merged key-risk area, for example Airborne collision, alongside category and severity score;
- single-cell layout tables such as Key principle are retained as callouts rather than misrepresented as relational table rows.

## Interpretation and remaining work

This acceptance concerns source parsing, identity, hierarchy, citations, ordering, and table context. It does not yet establish retrieval quality or answer correctness.

Before E1 retrieval scores can be compared with E0:

1. map each historical QA source chunk to one or more new parent IDs;
2. map the exact gold evidence to child IDs and manually resolve ambiguous matches;
3. freeze source-grouped development and test partitions;
4. build the E1 dense index with the same embedding model as E0;
5. evaluate child recall, parent recall, MRR, and nDCG before generation.

The 87 very short and 8 long children must be monitored in retrieval error analysis. They should not be merged or split merely to optimize aggregate length statistics; any adjustment must be justified by retrieval failures on development data.

## Reproduction

Use scripts/build_parent_child_corpus.py with the source, output, and document-version arguments recorded in manifest.json. The builder refuses to overwrite a non-empty output unless --force is explicitly provided.
