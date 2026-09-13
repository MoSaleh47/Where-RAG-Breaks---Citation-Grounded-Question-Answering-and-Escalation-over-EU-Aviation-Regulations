# Test Strategy

Tests are required before promoting data or results.

## Corpus tests

- deterministic parent and child IDs;
- unique IDs and valid parent references;
- regulation/document-type separation;
- hierarchy and citation normalization;
- no empty evidence text;
- bounded child token sizes;
- preserved table headers;
- resolvable source locations;
- representative ARTICLE, GM, ANNEX, and cross-reference fixtures.

## Retrieval tests

- deterministic rankings for fixed cached embeddings;
- cosine normalization;
- BM25 tokenization behavior for article numbers and acronyms;
- reciprocal-rank-fusion calculation;
- parent expansion and sibling deduplication;
- no hidden use of gold labels at runtime.

## Evaluation tests

- exact versus partial citations;
- multiple citations;
- alternative acceptable citations;
- citation presence independent of correctness;
- retrieval and generation failures can coexist;
- paired evaluation IDs are aligned;
- legacy metric reproduction.

## Safety tests

- unsupported answers trigger verification failure;
- ambiguous or conflicting evidence can abstain;
- returned citations resolve only to supplied source IDs;
- user-facing output states that qualified human verification is required.

