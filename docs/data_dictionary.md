# Parent–Child Data Dictionary

## Parent record

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `parent_id` | string | yes | Deterministic stable legal-unit ID |
| `document_id` | string | yes | Source document identifier |
| `document_version` | string | yes | Regulatory/source snapshot version |
| `regulation_id` | string | yes | Canonical regulation identity |
| `document_type` | enum | yes | ARTICLE, ANNEX, RECITALS, or GM |
| `hierarchy_path` | array[string] | yes | Ordered headings from document root |
| `canonical_citation` | string | yes | Normalized parent citation |
| `title` | string | yes | Human-readable unit heading |
| `text` | string | yes | Complete parent text |
| `source_location` | object | yes | Page, XML anchor, URL, or equivalent trace |
| `cross_references` | array[string] | no | Normalized referenced legal units |
| `char_count` | integer | yes | Parent text length in Unicode characters |
| `word_count` | integer | yes | Whitespace-delimited parent word count |
| `child_ids` | array[string] | yes | Ordered child identifiers |

## Child record

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `child_id` | string | yes | Deterministic stable evidence-unit ID |
| `parent_id` | string | yes | Existing parent record |
| `sequence` | integer | yes | Child order within parent |
| `canonical_citation` | string | yes | Exact paragraph/list/table citation |
| `unit_type` | enum | yes | paragraph, list_item, table_row, table_header, or callout |
| `text` | string | yes | Evidence text |
| `retrieval_text` | string | yes | Metadata-enriched text embedded/indexed |
| `char_count` | integer | yes | Evidence text length in Unicode characters |
| `word_count` | integer | yes | Whitespace-delimited evidence word count |
| `marker_path` | array[string] | yes | Structured nested list markers used by canonical citation |
| `source_location` | object | yes | Exact source trace |

## Integrity rules

- IDs are unique and reproducible from legal identity and hierarchy.
- Every child references exactly one existing parent.
- Canonical citations cannot be inferred only from free-form LLM output.
- Table rows repeat the relevant table and column headers in `retrieval_text`.
- Parent and child source locations resolve to the immutable source snapshot.
- Binding and guidance material are never silently merged into one type.

