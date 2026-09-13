#!/usr/bin/env python3
"""Aggregate multi-reviewer Google Form responses into the freeze-pipeline review queue.

Reads the CSV exported from the Google Sheet linked to the review form, computes
per-record vote tallies and inter-rater agreement, applies a PRE-REGISTERED
aggregation rule, and writes a review_queue.csv that
aviation_rag_research/scripts/freeze_reviewed_benchmark.py will accept.

Contract enforced by src/aviation_rag/evaluation/review.py:
  reviewer_decision  in {accept, accept_with_alternative_evidence, correct, exclude}
  4 check fields     in {yes, no, uncertain}
  'accept'           requires all four checks == yes
  reviewer_name_or_role non-empty; review_date ISO YYYY-MM-DD

Rows the panel does not unanimously clear are left with an EMPTY decision and
listed under "needs author adjudication" — you fill those in yourself, because
corrections and alternative evidence sets cannot come from a multiple-choice form.

Usage:
  python aggregate_reviews.py responses.csv review_queue.csv -o out/
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# PRE-REGISTERED AGGREGATION RULE  --  fix this BEFORE collecting responses
# ---------------------------------------------------------------------------
MIN_REVIEWERS = 2          # records with fewer raters are never auto-decided
REQUIRE_UNANIMOUS = False  # False = strict majority; True = every rater must agree
# ---------------------------------------------------------------------------

CHECK_FIELDS = (
    "question_clear_and_unambiguous",
    "answer_fully_supported",
    "citation_correct",
    "gold_evidence_complete",
)

Q_TO_FIELD = {
    "Q1": "question_clear_and_unambiguous",
    "Q2": "answer_fully_supported",
    "Q3": "citation_correct",
    "Q4": "gold_evidence_complete",
}

ANSWER_MAP = {
    "oui": "yes",
    "yes": "yes",
    "non": "no",
    "no": "no",
    "partiellement": "no",       # partial support does not clear 'accept'
    "partially": "no",
    "incertain": "uncertain",
    "unsure": "uncertain",
}

DECISION_MAP = {
    "accepter": "accept",
    "accept": "accept",
    "accepter avec correction": "correct",
    "accept with correction": "correct",
    "rejeter": "exclude",
    "reject": "exclude",
    "je passe cette fiche": "skip",
    "i skip this record": "skip",
}

# v2 form: the four validity checks are one grid item, exported by Google as
#   "QA_0011 | C - Evaluation / Assessment [1. Question claire ...]"
GRID_RE = re.compile(r"^\s*(QA_\d+)\s*\|\s*C\b.*\[\s*([1-4])\.")
# v1 form (and Q5/Q6 in both versions): "QA_0011 | Q5 - Decision globale ..."
HEADER_RE = re.compile(r"^\s*(QA_\d+)\s*\|\s*(Q[1-6])\b")


def norm(value: str) -> str:
    """Normalise a bilingual 'Oui / Yes' choice to its left-hand French token."""
    value = (value or "").strip()
    if not value:
        return ""
    head = value.split("/")[0].strip().lower()
    head = head.split(",")[0].strip()
    return head


def map_answer(value: str) -> str:
    return ANSWER_MAP.get(norm(value), "")


def map_decision(value: str) -> str:
    return DECISION_MAP.get(norm(value), "")


# ---------------------------------------------------------------------------
# agreement statistics (pure python, no scipy)
# ---------------------------------------------------------------------------
def fleiss_kappa(table: list[list[int]]) -> float | None:
    """Fleiss' kappa, generalised to a variable number of raters per item.

    table[i] = category counts for item i. Items rated by fewer than two raters
    are dropped. Unlike the equal-n formulation, no item is silently discarded
    for having a different rater count -- with partial response coverage that
    would compute the statistic on an unrepresentative subset.
    """
    table = [row for row in table if sum(row) > 1]
    if not table:
        return None
    n_i = [sum(row) for row in table]
    total = sum(n_i)
    k = len(table[0])
    p_j = [sum(row[j] for row in table) / total for j in range(k)]
    P_i = [
        (sum(c * c for c in row) - n) / (n * (n - 1))
        for row, n in zip(table, n_i)
    ]
    P_bar = sum(P_i) / len(P_i)
    P_e = sum(p * p for p in p_j)
    if abs(1 - P_e) < 1e-12:
        return None
    return (P_bar - P_e) / (1 - P_e)


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if len(pairs) < 2:
        return None
    cats = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    if len(cats) < 2:
        return None
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if abs(1 - pe) < 1e-12:
        return None
    return (po - pe) / (1 - pe)


def interpret(kappa: float | None) -> str:
    if kappa is None:
        return "not computable"
    for threshold, label in (
        (0.0, "poor"), (0.20, "slight"), (0.40, "fair"),
        (0.60, "moderate"), (0.80, "substantial"),
    ):
        if kappa <= threshold:
            return label
    return "almost perfect"


def majority(values: list[str], unanimous: bool) -> tuple[str, bool]:
    """Return (winner, contested). Empty values are ignored."""
    values = [v for v in values if v]
    if not values:
        return "", True
    counts = Counter(values)
    top, top_n = counts.most_common(1)[0]
    if unanimous:
        return (top, len(counts) > 1)
    tied = sum(1 for v in counts.values() if v == top_n) > 1
    return (top, tied or top_n <= len(values) / 2)


# ---------------------------------------------------------------------------
def load_responses(path: Path) -> tuple[list[dict], dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        headers = reader.fieldnames or []

    col_index: dict[tuple[str, str], str] = {}
    for header in headers:
        grid = GRID_RE.match(header)
        if grid:                                   # v2 grid column -> Q1..Q4
            col_index[(grid.group(1), "Q" + grid.group(2))] = header
            continue
        match = HEADER_RE.match(header)
        if match:
            col_index[(match.group(1), match.group(2))] = header

    def profile_col(tag: str) -> str:
        for header in headers:
            if header.strip().startswith(tag):
                return header
        return ""

    meta = {
        "col_index": col_index,
        "name": profile_col("R1."),
        "experience": profile_col("R2."),
        "familiarity": profile_col("R3."),
        "timestamp": headers[0] if headers else "",
    }
    return rows, meta


def parse_timestamp(raw: str) -> date | None:
    raw = (raw or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("responses", type=Path, help="CSV exported from the response Sheet")
    parser.add_argument("queue", type=Path, help="original review_queue.csv")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("."))
    parser.add_argument("--min-reviewers", type=int, default=MIN_REVIEWERS)
    parser.add_argument("--unanimous", action="store_true", default=REQUIRE_UNANIMOUS)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    responses, meta = load_responses(args.responses)
    if not responses:
        print("No responses found.", file=sys.stderr)
        return 1

    with args.queue.open(encoding="utf-8-sig", newline="") as handle:
        queue_reader = csv.DictReader(handle)
        queue_rows = list(queue_reader)
        queue_fields = queue_reader.fieldnames or []

    qa_ids = [row["qa_id"] for row in queue_rows]

    # ---- collect votes -----------------------------------------------------
    votes: dict[str, dict[str, list]] = {
        qa: {"decision": [], "checks": defaultdict(list), "notes": [], "raters": []}
        for qa in qa_ids
    }
    reviewers: list[dict] = []

    for response in responses:
        name = (response.get(meta["name"], "") or "anonymous").strip()
        experience = (response.get(meta["experience"], "") or "").strip()
        familiarity = (response.get(meta["familiarity"], "") or "").strip()
        stamp = parse_timestamp(response.get(meta["timestamp"], ""))
        answered = 0

        for qa in qa_ids:
            decision_col = meta["col_index"].get((qa, "Q5"))
            decision = map_decision(response.get(decision_col, "")) if decision_col else ""
            check_values = {}
            for tag, field in Q_TO_FIELD.items():
                col = meta["col_index"].get((qa, tag))
                check_values[field] = map_answer(response.get(col, "")) if col else ""

            if not decision and not any(check_values.values()):
                continue           # reviewer skipped this record entirely
            if decision == "skip":
                continue

            answered += 1
            votes[qa]["raters"].append(name)
            if decision:
                votes[qa]["decision"].append(decision)
            for field, value in check_values.items():
                if value:
                    votes[qa]["checks"][field].append(value)

            note_col = meta["col_index"].get((qa, "Q6"))
            note = (response.get(note_col, "") or "").strip() if note_col else ""
            if note:
                votes[qa]["notes"].append(f"{name}: {note}")

        reviewers.append({"name": name, "experience": experience,
                          "familiarity": familiarity, "date": stamp, "answered": answered})

    # ---- aggregate ---------------------------------------------------------
    aggregate_rows = []
    auto_decided = 0
    needs_author = []

    for row in queue_rows:
        qa = row["qa_id"]
        v = votes[qa]
        n = len(v["raters"])

        decision_win, decision_contested = majority(v["decision"], args.unanimous)
        check_results = {}
        checks_contested = False
        for field in CHECK_FIELDS:
            winner, contested = majority(v["checks"][field], args.unanimous)
            check_results[field] = winner or "uncertain"
            checks_contested = checks_contested or contested

        counts = Counter(v["decision"])
        enough = n >= args.min_reviewers
        all_yes = all(check_results[f] == "yes" for f in CHECK_FIELDS)

        final = ""
        reason = ""
        if not enough:
            reason = f"only {n} reviewer(s), need {args.min_reviewers}"
        elif decision_contested or checks_contested:
            reason = "reviewers disagree"
        elif decision_win == "accept" and all_yes:
            final = "accept"
        elif decision_win == "accept" and not all_yes:
            reason = "majority accepts but a validity check is not 'yes'"
        elif decision_win == "exclude":
            final = "exclude"
        elif decision_win == "correct":
            reason = "panel wants a correction - you must supply the corrected fields"
        else:
            reason = "no usable majority"

        if final:
            auto_decided += 1
        else:
            needs_author.append((qa, reason))

        aggregate_rows.append({
            "qa_id": qa,
            "source_class": row.get("source_class", ""),
            "review_reason": row.get("review_reason", ""),
            "n_reviewers": n,
            "reviewers": "; ".join(v["raters"]),
            "votes_accept": counts.get("accept", 0),
            "votes_correct": counts.get("correct", 0),
            "votes_exclude": counts.get("exclude", 0),
            **{f"agg_{f}": check_results[f] for f in CHECK_FIELDS},
            "panel_verdict": decision_win,
            "contested": "yes" if (decision_contested or checks_contested) else "no",
            "auto_decision": final,
            "action_needed": reason,
            "comments": " || ".join(v["notes"]),
        })

        # write back into the queue row
        if final:
            row["reviewer_decision"] = final
            for field in CHECK_FIELDS:
                row[field] = check_results[field]
            roles = "; ".join(sorted(set(v["raters"])))
            row["reviewer_name_or_role"] = f"panel({n}): {roles}"[:250]
            dates = [r["date"] for r in reviewers if r["date"]]
            row["review_date"] = (max(dates) if dates else date.today()).isoformat()
            tally = (f"panel accept={counts.get('accept',0)} "
                     f"correct={counts.get('correct',0)} exclude={counts.get('exclude',0)}")
            row["review_notes"] = (tally + (" || " + " || ".join(v["notes"]) if v["notes"] else ""))[:900]

    # ---- write outputs -----------------------------------------------------
    agg_path = args.outdir / "review_aggregate.csv"
    with agg_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate_rows[0].keys()))
        writer.writeheader()
        writer.writerows(aggregate_rows)

    filled_path = args.outdir / "review_queue_filled.csv"
    with filled_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=queue_fields)
        writer.writeheader()
        writer.writerows(queue_rows)

    # ---- agreement ---------------------------------------------------------
    per_record = defaultdict(list)
    for response in responses:
        name = (response.get(meta["name"], "") or "anonymous").strip()
        for qa in qa_ids:
            col = meta["col_index"].get((qa, "Q5"))
            decision = map_decision(response.get(col, "")) if col else ""
            if decision and decision != "skip":
                per_record[qa].append((name, decision))

    shared = {qa: v for qa, v in per_record.items() if len(v) >= 2}
    kappa_f = None
    kappa_bin = None
    if shared:
        cats = ["accept", "correct", "exclude"]
        table = []
        for v in shared.values():
            counter = Counter(d for _, d in v)
            table.append([counter.get(c, 0) for c in cats])
        kappa_f = fleiss_kappa(table)
        bin_table = []
        for v in shared.values():
            counter = Counter("accept" if d == "accept" else "change" for _, d in v)
            bin_table.append([counter.get("accept", 0), counter.get("change", 0)])
        kappa_bin = fleiss_kappa(bin_table)

    kappa_c = None
    names = [r["name"] for r in reviewers]
    if len(set(names)) == 2:
        a, b = sorted(set(names))
        pairs = []
        for qa, v in per_record.items():
            da = next((d for n_, d in v if n_ == a), None)
            db = next((d for n_, d in v if n_ == b), None)
            if da and db:
                pairs.append((da, db))
        kappa_c = cohen_kappa(pairs)

    exact = sum(1 for v in shared.values() if len({d for _, d in v}) == 1)
    pct = exact / len(shared) * 100 if shared else None

    # ---- report ------------------------------------------------------------
    lines = []
    add = lines.append
    add("=" * 68)
    add("MULTI-REVIEWER BENCHMARK REVIEW - AGGREGATION REPORT")
    add("=" * 68)
    add(f"Aggregation rule : {'unanimous' if args.unanimous else 'strict majority'}, "
        f"min {args.min_reviewers} reviewers")
    add(f"Reviewers        : {len(reviewers)}")
    for r in reviewers:
        add(f"  - {r['name']:<28} {r['answered']:>2} records | {r['experience']} | {r['familiarity']}")
    add("")
    add(f"Records total            : {len(queue_rows)}")
    add(f"Records with >=1 rating  : {sum(1 for r in aggregate_rows if r['n_reviewers'] > 0)}")
    add(f"Records with >=2 ratings : {len(shared)}")
    add(f"Auto-decided by panel    : {auto_decided}")
    add(f"Need your adjudication   : {len(needs_author)}")
    add("")
    add("--- inter-rater agreement (on the overall decision) ---")
    if pct is not None:
        add(f"Exact agreement    : {exact}/{len(shared)} = {pct:.1f}%")
    if kappa_c is not None:
        add(f"Cohen's kappa      : {kappa_c:.3f}  ({interpret(kappa_c)})")
    if kappa_f is not None:
        add(f"Fleiss' kappa      : {kappa_f:.3f}  ({interpret(kappa_f)})  [3 categories]")
    if kappa_bin is not None:
        add(f"Fleiss' kappa      : {kappa_bin:.3f}  ({interpret(kappa_bin)})  "
            f"[accept vs needs-change, POST-HOC collapse -- label it as such]")
    if pct is None:
        add("Not computable - no record has two or more reviewers yet.")
    add("")
    add("--- records still needing you ---")
    for qa, reason in needs_author:
        add(f"  {qa}: {reason}")
    add("")
    add(f"Wrote {agg_path}")
    add(f"Wrote {filled_path}")
    add("")
    add("NEXT: fill the blank reviewer_decision rows in review_queue_filled.csv,")
    add("      copy it over data/evaluation/independent_review_v1/review_queue.csv,")
    add("      then run scripts/freeze_reviewed_benchmark.py")
    add("=" * 68)

    report = "\n".join(lines)
    print(report)
    (args.outdir / "review_agreement_report.txt").write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
