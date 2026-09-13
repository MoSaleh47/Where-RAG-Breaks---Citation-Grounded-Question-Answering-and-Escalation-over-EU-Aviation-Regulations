#!/usr/bin/env python3
"""Split a raw Google Forms response export into a pseudonymised file and a private key.

The pseudonymised file is safe to keep in the repository and to cite in the
memoire. The key file maps pseudonyms back to identities and must NOT be
committed, published, or included in any appendix.

Usage:
  python pseudonymise_responses.py raw_responses.csv -o outdir/
"""
from __future__ import annotations
import argparse, csv, hashlib
from pathlib import Path

NAME_PREFIX = "R1."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("responses", type=Path)
    ap.add_argument("-o", "--outdir", type=Path, default=Path("."))
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    with args.responses.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        headers = reader.fieldnames or []

    name_col = next((h for h in headers if h.strip().startswith(NAME_PREFIX)), None)
    exp_col = next((h for h in headers if h.strip().startswith("R2.")), None)
    fam_col = next((h for h in headers if h.strip().startswith("R3.")), None)
    if not name_col:
        raise SystemExit("No 'R1.' name column found in the export.")

    mapping: dict[str, str] = {}
    key_rows = []
    for row in rows:
        raw = (row.get(name_col) or "").strip()
        if raw not in mapping:
            pseudo = f"R{len(mapping) + 1}"
            mapping[raw] = pseudo
            key_rows.append({
                "pseudonym": pseudo,
                "declared_name_or_role": raw,
                "experience": (row.get(exp_col) or "").strip() if exp_col else "",
                "familiarity": (row.get(fam_col) or "").strip() if fam_col else "",
                "sha256_of_declared_value": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            })
        row[name_col] = mapping[raw]

    pseudo_path = args.outdir / "responses_pseudonymised.csv"
    with pseudo_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    key_path = args.outdir / "reviewer_key_PRIVATE.csv"
    with key_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(key_rows[0].keys()))
        w.writeheader()
        w.writerows(key_rows)

    print(f"{len(mapping)} reviewer(s) pseudonymised")
    for k in key_rows:
        print(f"  {k['pseudonym']} <- {k['declared_name_or_role'][:50]}")
    print(f"\nWrote {pseudo_path}")
    print(f"Wrote {key_path}   <-- PRIVATE. Do not commit, publish, or append to the memoire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
