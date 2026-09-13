# LaTeX mémoire source

This directory is the project-specific report derived from the official aivancity English template. The originals under `Guide/PFE_Template/` remain unchanged.

## Build

From this directory:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
biber main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

If Perl and `latexmk` are installed, `latexmk -pdf -interaction=nonstopmode main.tex` is an equivalent convenience command. After render-and-visual QA, copy the validated PDF to `../../output/pdf/PFE_working_draft.pdf`.

## Source status - 25 July 2026

- State of the Art and Methodology were expanded after the current packaged PDF was produced.
- `references.bib` contains 64 entries; `references_pre_expansion_2026-07-23.bib` preserves the 10-entry predecessor.
- Expanded chapters are AI-assisted drafts marked `pending-author-edit` in `docs/generated_artifacts_log.md` and must be read and rewritten in the student's voice.
- Candidate retrieval values remain visibly marked.
- Final generation, verification, switching-policy, conclusion, and abstract claims remain provisional.
- The current source must be rebuilt and visually inspected before a new page count or PDF status is reported.

## Mandatory unresolved fields

Edit `metadata.tex` to provide the student name, host company, industry supervisor, academic supervisor surname, and defence date. Complete the company context, acknowledgements, final abstract/résumé, and AI-use disclosure with the student's own verified information.
