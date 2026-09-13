# Legacy-to-E1 Source Mapping Audit

**Run date:** 17 July 2026  
**Input:** 132 historical flat chunks and 300 synthetic QA records  
**Target:** 109 validated E1 parent records  
**Purpose:** preserve lineage while preventing invalid legacy sources from entering the new evaluation set.

## Result

| QA mapping status | Count | Use |
|---|---:|---|
| Automatically mapped by normalized equality/containment | 291 | Candidate for child-level evidence audit |
| Manually accepted | 4 | Candidate for child-level evidence audit |
| Excluded: invalid source | 4 | Do not use in E1 evaluation |
| Rewrite required | 1 | Rewrite and re-audit before use |

All 300 QA records now have an explicit disposition. No unresolved fuzzy mapping is silently treated as gold.

At chunk level, 113 of 132 legacy chunks map automatically. The remaining 19 require review, but only four of those chunks are used by QA records without an automatic mapping. Their nine QA records were resolved individually.

## Manual resolutions

| Legacy chunk | QA IDs | Resolution |
|---|---|---|
| CHUNK_0003 | QA_0000 | Rewrite against EU_2021_2082_ART_6; the original source is editorial front matter. |
| CHUNK_0003 | QA_0001 | Exclude; an editor contact email is outside aviation-regulation QA. |
| CHUNK_0009 | QA_0002 to QA_0004 | Exclude; the source is concatenated table-of-contents text and the answers are tautological. |
| CHUNK_0082 | QA_0152, QA_0153 | Accept GM_EU_376_2014_SEC_2_3; formatting differences prevented exact containment. |
| CHUNK_0131 | QA_0246, QA_0247 | Accept GM_EU_376_2014_ACRONYMS after repairing its parent boundary. |

## Historical headline-sample correction

QA_0003 is one of the 100 records in the stored few-shot/RAG/LoRA comparison. It was generated from table-of-contents text, its answer merely points back to Section 2.2, and it must not be treated as valid legal QA.

The stored results remain immutable and must still be reported as the historical 100-record view. A sensitivity view excluding QA_0003 is:

| System | Variant | N | ROUGE-L | Mean citation match | Proxy passes | Exact citation + content passes | Retrieval success |
|---|---:|---:|---:|---:|---:|---:|---:|
| Few-shot | k=10 | 99 | 0.2662 | 0.1919 | 28/99 | 9/99 | n/a |
| RAG | k=5 | 99 | 0.4411 | 0.5354 | 63/99 | 43/99 | 82/99 |
| LoRA | 3B | 99 | 0.2796 | 0.1667 | 19/99 | 11/99 | n/a |

The ranking and numerators do not change because every system failed the legacy citation criterion on QA_0003. The denominator and mean metrics do change. This supports the existing decision to use the old sample only for continuity, not final claims.

## Method

The deterministic mapper uses this precedence:

1. normalized text equality;
2. legacy text wholly contained in a new parent;
3. a single new parent wholly contained in a legacy chunk;
4. fuzzy token coverage and cosine ranking, marked review-required rather than accepted.

QA-level overrides record accept, rewrite, or exclude decisions with notes. Input and output SHA-256 hashes are stored in mapping_summary.json.

## Generated artifacts

The directory data/evaluation/legacy_to_e1_v1 contains:

- legacy_chunk_parent_map.csv: all 132 flat chunks, candidates, scores, margins, and status;
- qa_parent_map.csv: the disposition and parent lineage for all 300 QA records;
- mapping_summary.json: counts and hashes.

The review decisions are versioned separately in data/evaluation/legacy_qa_mapping_overrides.csv.

## Remaining gate

Parent mapping is not exact evidence mapping. Before freezing the E1 evaluation set:
## Child-evidence review queue

Lexical and citation-aware ranking produced up to five child candidates for every one of the 295 accepted QA records. These are review suggestions, not gold labels.

| Review priority | Count |
|---|---:|
| High | 129 |
| Medium | 103 |
| Low | 63 |


1. review the ranked child candidates and select one or more exact evidence IDs;
2. test whether the stored answer is fully supported by those children;
3. correct or exclude ambiguous, incomplete, and synthetic-hallucinated answers;
4. split by parent ID so no parent leaks across development and test;
5. preserve a locked manifest and report all exclusions.
