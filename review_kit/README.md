# Benchmark review kit — multi-reviewer collection

Turns the 0/33 `review_queue.csv` blocker into a bilingual FR/EN Google Form your
aviation colleagues can fill from a link, plus aggregation back into the exact
format `scripts/freeze_reviewed_benchmark.py` accepts.

| File | What it is |
|---|---|
| `build_review_form.gs` | Google Apps Script. Paste once, run once, get a form + a live response Sheet. All 33 records embedded. |
| `aggregate_reviews.py` | Reads the exported response CSV → vote tallies, inter-rater agreement, and a pre-filled `review_queue.csv`. |
| `REVIEW_PROTOCOL_D023.md` | The pre-registered aggregation rule and decision-log entries. **Read this first.** |

---

## Step 1 — protocol registered

D023/D024 were added to `docs/decision_log.md` on 25 July 2026 before collection.
Do not add duplicate entries. If the aggregation rule changes after responses are
seen, record a new decision and report results under both rules.

## Step 2 — build the form

1. Open <https://script.google.com> → **New project**
2. Delete the sample code, paste **all** of `build_review_form.gs`
3. **Save**, then **Run → `buildReviewForm`**
4. Authorise when Google asks (it's your own account; the "unverified app" warning is expected — *Advanced → Go to project*)
5. The **links appear in the log within a few seconds** — form link, edit link, Sheet link. Save them somewhere.
6. If the log ends with `RUN buildReviewForm AGAIN`, run it again. Repeat until `BUILD COMPLETE`. Usually 1–2 runs.

Then open the form → **Send → link settings → turn OFF "Restrict to users in your
organisation"**, otherwise external colleagues get a permission wall.

**If a run seems stuck:** Google kills any Apps Script execution at 6 minutes.
This builder saves progress after every block and logs the links first, so a
timeout costs you nothing — just run it again. `showLinks()` reprints the links
and the block count without building anything. `resetReviewForm()` clears
progress if you want to start a fresh form (delete the old one in Drive first).

## Step 3 — send it

Each record shows the question, the proposed answer, the citation, and **the exact
regulatory text** — everything needed to judge it, no external lookup. Five
multiple-choice questions plus an optional comment, ~2 minutes per record.

After every block of 6, the reviewer chooses to continue or submit. **Partial
responses are fully usable** — someone who does 12 records still counts. Say this
explicitly when you send the link; it roughly doubles response rates versus an
all-or-nothing ask.

Suggested message:

> Bonjour — je termine mon PFE sur la recherche documentaire automatisée dans la
> réglementation aérienne (Règlement UE 376/2014). J'ai besoin de professionnels
> pour vérifier si des réponses générées automatiquement sont réellement
> justifiées par le texte réglementaire. Tout le texte nécessaire est fourni dans
> le formulaire — aucune recherche à faire. ~2 min par fiche, et vous pouvez vous
> arrêter quand vous voulez, les réponses partielles me sont utiles. Merci !

Aim for **3+ reviewers** — that unlocks Fleiss' κ. With 2 you get Cohen's κ. With
1 the agreement statistic doesn't exist and you're back to author adjudication.

## Step 4 — aggregate

In the response Sheet: **File → Download → Comma Separated Values**, then:

```bash
python aggregate_reviews.py responses.csv \
    aviation_rag_research/data/evaluation/independent_review_v1/review_queue.csv \
    -o out/
```

Pure standard library, no dependencies. Produces:

- `review_aggregate.csv` — per record: rater count, vote tallies, panel verdict, contested flag, comments
- `review_queue_filled.csv` — the real queue with panel-cleared rows filled in; contested rows left blank for you
- `review_agreement_report.txt` — reviewer roster, agreement %, Cohen's/Fleiss' κ, and the list of records still needing you

Options: `--min-reviewers N` (default 2), `--unanimous` (default: strict majority).

## Step 5 — adjudicate the rest, then freeze

Fill the blank `reviewer_decision` rows yourself. Allowed values, enforced by
`review.py`:

| Value | Requires |
|---|---|
| `accept` | all four checks `yes`, no alternatives supplied |
| `accept_with_alternative_evidence` | first three checks `yes` + `alternative_evidence_sets_json` |
| `correct` | at least one `corrected_*` field |
| `exclude` | — |

Checks are `yes` / `no` / `uncertain`. `reviewer_name_or_role` non-empty,
`review_date` as `YYYY-MM-DD`.

Then copy `review_queue_filled.csv` over
`data/evaluation/independent_review_v1/review_queue.csv` and run
`scripts/freeze_reviewed_benchmark.py`. It refuses incomplete data by design — if
it complains, a row is still blank or malformed.

Once it passes, regenerate retrieval and reranking metrics against the frozen labels. Only those regenerated values may replace the candidate figures. E5 generation is then unblocked with respect to benchmark validity, but model selection and separate hosted-generation authorization still remain.

---

## Verification performed

- `build_review_form.gs` (v2) parses cleanly (`node --check`); all 33 records embedded; longest payload ~1.9k chars, well under the Forms field limit
- v2 makes ~142 API calls instead of ~231, logs the links before doing any slow work, and resumes from saved progress after a timeout
- `aggregate_reviews.py` round-tripped against synthetic responses in **both** the v2 grid layout and the v1 layout — 3 reviewers, partial completion, skips, ties, disagreement
- every auto-decided row in those tests validated against the **real** `ALLOWED_DECISIONS` / `CHECK_FIELDS` contract imported from your `review.py` — **0 errors**
- κ computation checked against the Fleiss and Cohen definitions
