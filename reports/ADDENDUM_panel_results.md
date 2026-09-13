# Addendum — first panel results (30 July 2026)

Read this alongside `SPEAKER_NOTES_31july2026.md`. The deck is now 13 slides;
slide 9 is new.

---

## What the data actually says

| Quantity | Value |
|---|---|
| Reviewers | 2, both with 10+ years in aviation |
| R1 | Familiar with Reg. 376/2014; 22 records rated |
| R2 | Works directly with Reg. 376/2014; 12 records rated |
| Records rated at least once | 27 / 33 |
| Records rated by both | **7** |
| Exact agreement on the overall decision | 4 / 7 = 57.1% |
| Cohen's κ | 0.323 (fair, Landis & Koch) |
| Panel-cleared automatically | 2 (QA_0047 accept, QA_0063 exclude) |
| Requiring your adjudication | 31 |
| Records with zero ratings | 6 |

---

## The two results worth presenting

### 1. QA_0063 was independently confirmed

Both reviewers voted to **exclude** it, unanimously, without being told your
hypothesis. R1's comment explains why in one line: the question asks "what
exceptions are noted in Regulation 376/2014?" but the provisions in question
concern only document access and data protection — *"La question ne précise pas
cela."*

You argued from internal evidence that this record was an ambiguous question
rather than a retrieval failure. Two aviation professionals reached the same
conclusion independently. **This is the strongest single thing you have.**

### 2. An unplanned finding: your citation labels are not readable

Six records drew the same reaction from R1, in different words each time:

> *"GM 3.1 = ?"* · *"GM 3.4 = ?"* · *"GM 4.2. = ?"* · *"qu'entends-tu par 'section 2.2'?"* · *"qu'entends-tu par 'subject matter'?"* · *"qu'entends-tu par 'Annex II, item 3.14'?"*

A practitioner who works with this regulation daily could not resolve your
canonical citation strings. That is a defect in citation **formatting**, not in
the individual records — and no automatic metric in your pipeline would ever have
surfaced it, because every one of those citations is internally consistent and
resolves correctly against your own corpus.

This is exactly the kind of finding that justifies the whole exercise: it is
invisible from inside the system and obvious to an outside reader. Say so.

### 3. Substantive errors caught (mention briefly)

- **QA_0040** — R2: Article 12(1) has nothing to do with a timeline
- **QA_0097** — R2: 2020/2034 is not cited in 376/2014
- **QA_0163** — R1: Article 4(6) does not discuss lack of trust in one's organisation
- **QA_0287** — R1: Article 5(1)–(2) concerns *voluntary* reports
- **QA_0003** — R1: saying "individuals" is reductive; it is organisations that must report
- **QA_0080** — R2: the correct terms are occurrence category and activity category

---

## How to present the kappa — carefully

**Say this:** "Agreement on the seven records both reviewers rated is 57 per cent
exact, Cohen's kappa 0.32. That is fair agreement on the conventional scale, but
on seven records it is a first measurement, not a stable estimate — one record
flipping moves it substantially. I'm reporting it because the protocol requires
me to report it, not because I'd defend the number."

**Do not say:** "we achieved fair inter-rater agreement." That invites a question
about n that you would rather ask yourself.

The honest framing is stronger anyway: three disagreements out of seven, on a
benchmark you built, is itself evidence that these records are genuinely hard —
which is the thesis.

---

## What changed in the deck

| Slide | Change |
|---|---|
| 9 (new) | First panel results: the four figures, QA_0063 confirmed, the citation-legibility finding |
| 11 | Status kicker now 30 July; blocked list shows real coverage; the red line is now the freeze rule, not "the review is the critical path" |
| 13 | Decision 1 rewritten: the ask is no longer "is a panel enough" but "is 7 overlapping records enough, or do I re-issue for the 26 single-rated ones" |

---

## Revised ask for slide 13

The coverage question has changed shape. What you now need from him:

> "Two reviewers responded, but only seven records were rated by both, so my
> agreement statistic rests on seven observations. I can either freeze on 6 August
> with that, and report the coverage exactly as it is — or re-issue the form asking
> specifically for the 26 records that currently have a single rating, which would
> give me a real agreement estimate at the cost of a few days. My inclination is the
> second, targeted at the overlap rather than at everyone. What's your view?"

That is a good question to bring a supervisor. It has a defensible answer either
way, you have a recommendation, and it shows you understand what the statistic
does and doesn't support.

---

## Anonymisation — done, and what remains

`review_kit/pseudonymise_responses.py` now produces:

- `review_kit/_private/responses_pseudonymised.csv` — reviewers appear as R1, R2. Safe for the repository and the mémoire.
- `review_kit/_private/reviewer_key_PRIVATE.csv` — the mapping. **Never commit, publish, or append this.**

The aggregation was re-run on the pseudonymised file, so the outputs in
`review_kit/out_2026-07-30/` carry pseudonyms only.

**Two things still on you:**

1. **Delete or move the raw export.** `review_kit/PFE - Reponses revue benchmark ... .csv` still contains both reviewers' names. It should not sit in a directory you might share or submit. Move it into `_private/` alongside the key.
2. **Get consent for how you describe them.** In the mémoire, report role, years of experience and familiarity — never names. One of your reviewers works at a national civil aviation authority, which is a genuinely strong qualification claim; ask whether you may say "a safety analyst at a national civil aviation authority" or whether they'd prefer "a safety specialist with over ten years' experience". Ask before you write it, not after.

Names, employer and expressed opinions together are personal data. Pseudonymising
the analysis and keeping the key separate is the proportionate handling, and it
costs you nothing analytically — the agreement statistics are identical either way.
