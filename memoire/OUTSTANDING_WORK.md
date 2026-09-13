# Outstanding work — extracted from the LaTeX draft notes

Draft notes are now hidden in the compiled PDF (`\showdraftsfalse` in `main.tex`).
Nothing was deleted: set `\showdraftstrue` to bring them back on the page.
This file is the checklist they represented.


## `appendices/A_reproducibility.tex`

- Before final submission, export the exact Python and package versions, operating system, GPU, random seeds, hosted API model identifiers, request counts, token counts, latency, and monetary cost into a final environment table.

## `appendices/B_ai_disclosure.tex`

- Before submission, add the exact product/model names, approximate dates, tasks, and level of use requested by the school, and confirm this wording with the academic supervisor.

## `chapters/02_state_of_art.tex`

- Bibliography expanded to 64 verified references. Every entry cited in this chapter was checked against a primary record (ACL Anthology, PMLR, NeurIPS, ACM, JSTOR, EUR-Lex, or the publisher of record). Numerical results attributed to prior work are quoted from the cited papers and have not been reproduced here.

## `chapters/03_project_context.tex`

- This section requires facts that only the student can supply: the host company name, the department and team, the industry-supervisor's role, a factual description of the organisation's data and AI activity, and confirmation of any confidentiality restriction on naming the organisation or describing its internal processes. Everything else in this chapter is drawn from stored project artefacts and can stand as written.
- Before submission, verify directly against the corpus and add one worked example: a question, the provision that answers it, and the neighbouring provision that qualifies it. A concrete instance is worth more than the general argument above, and the material to build it is in `data/processed/E1_parent_child_v1/`.

## `chapters/04_methodology.tex`

- Every quantity in this chapter is taken from a stored manifest, validation record, or experiment output rather than from prose. Values that appear only in a written report and not in a machine-readable artefact are attributed to that report explicitly. Retrieval percentages remain candidate figures until the independent review described in Section~(sec:method-review) is complete.
- The manifest records the primary corpus with `version = 2022-12`, while the file name, the build manifest, and the corpus audit all describe it as a 27 September 2023 export. Both are correct –- it is the December 2022 revision of the Easy Access Rules, exported in September 2023 –- but the chapter should state both explicitly rather than choose one.
- The independent review is not yet complete. No candidate retrieval percentage in this document is a final benchmark claim until this gate has been passed and the benchmark frozen.

## `chapters/05_results.tex`

- Blocked until the benchmark review is frozen and a generator protocol is authorised. This section will compare compact and adjacent context variants, and, if approved, a stronger-model escalation on difficult cases only.

## `chapters/06_conclusion.tex`

- This is an interim conclusion. Replace it only after the reviewed benchmark, generation evaluation, switching calibration, and prototype evaluation are complete. No new result may be introduced here.

## `frontmatter/abstract.tex`

- Provisional abstract. Replace candidate findings after the independent benchmark review and end-to-end generation experiment. Final length: 250–300 words with no unexplained acronyms.

## `frontmatter/acknowledgements.tex`

- This personal section must be written or approved by the student and must not exceed one page.

## `frontmatter/resume_fr.tex`

- R\'{e}sum\'{e} provisoire. Il devra contenir 250–300 mots et \^{e}tre valid\'{e} par l'\'{e}tudiant apr\`{e}s les exp\'{e}riences finales.
