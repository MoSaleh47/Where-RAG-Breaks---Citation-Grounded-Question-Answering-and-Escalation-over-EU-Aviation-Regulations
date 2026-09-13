"""Parse legal citations from free text and resolve them against the E1 corpus.

The legacy baseline evaluator scored a citation as correct whenever the gold
string occurred anywhere in the prediction, and gave half credit for naming the
right article number alone. Both are unsound. Substring containment makes
``Article 4`` match inside ``Article 4(6)`` and ``Section 1`` match inside
``section 1.2``; half credit for the article number then passes a ``>= 0.5``
threshold and is counted as correct.

This module replaces that with two defined quantities.

``parent`` level
    The citations named in a prediction are resolved against the parent corpus.
    A prediction is parent-correct when the reviewed gold parent is among the
    parents it resolves to. Only parent identifiers that actually exist in the
    corpus are ever emitted, so this level is verifiable against a stored
    artifact rather than against a string.

``exact`` level
    Every atomic unit of the reviewed gold citation, down to the sub-paragraph,
    must be named in the prediction. Units are compared as structured tuples, so
    ``Article 4`` does not satisfy a gold of ``Article 4(6)`` and vice versa.

Ambiguity is explicit rather than hidden. The corpus contains four regulations
that each have an ``Article 1``, so a bare ``Article 1`` cannot be resolved from
the string alone. When a prediction names no regulation, the unit is attributed
to Regulation (EU) No 376/2014, the subject of the benchmark, and the unit is
flagged ``defaulted``. Callers are expected to report how many resolutions
relied on that assumption, because it can only inflate the parent-level score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_REGULATION = "376/2014"

REGULATION_PREFIX = {
    "376/2014": "EU_376_2014",
    "2015/1018": "EU_2015_1018",
    "2020/2034": "EU_2020_2034",
    "2021/2082": "EU_2021_2082",
}

_REGULATION_PATTERN = re.compile(
    r"\b(?:no\.?\s*)?(376\s*/\s*2014|2015\s*/\s*1018|2020\s*/\s*2034|2021\s*/\s*2082)\b"
)

# "Article 4", "Articles 20", "Art. 7"
_ARTICLE_PATTERN = re.compile(r"\barticles?\b\.?\s*(\d{1,3})|\bart\.\s*(\d{1,3})")
# "GM 3.1", "GM3.1"
_GM_PATTERN = re.compile(r"\bgm\s*(\d{1,2})\.(\d{1,2})\b")
_ANNEX_PATTERN = re.compile(r"\bannex\b(?:\s+(v|iv|iii|ii|i)\b)?")
_RECITAL_PATTERN = re.compile(r"\brecitals?\s+(\d{1,3})\b")

# Sub-paragraph run directly after an article number:
#   "(1)", "(1)(a)", "(1), (2) and (3)", "(11)-(12)", "(1)–(2)"
_SUB_RUN = re.compile(r"^(\s*(?:\(\s*[0-9a-z]{1,3}\s*\)|,|;|\s|and|to|-|–|—)+)")
_SUB_TOKEN = re.compile(r"\(\s*([0-9a-z]{1,3})\s*\)")
# "Article 13, paragraph 1" / "paragraphs 4 and 5"
_PARAGRAPH_RUN = re.compile(r"^\s*,?\s*paragraphs?\s+([0-9]{1,3}(?:\s*(?:,|and|to|-|–)\s*[0-9]{1,3})*)")
_RANGE_SEPARATORS = ("-", "–", "—", " to ")
# Elliptical continuation: "Article 7(4) and 7(8)", "Articles 20(1)-(2), 10 and 11".
# Only commas, semicolons and the words and/to may join them -- never a full stop,
# so the parser cannot run across a sentence boundary and invent a citation.
_CONTINUATION = re.compile(r"^(?:\s*(?:,|;|and|to)\s*)+(\d{1,3})")


@dataclass(frozen=True)
class Citation:
    """One atomic citation, e.g. Article 4(6)(a) of Regulation (EU) No 376/2014."""

    regulation: str
    kind: str  # ARTICLE | GM | ANNEX | RECITALS
    number: str
    subs: tuple[str, ...] = ()
    defaulted_regulation: bool = False

    def key(self) -> tuple[str, str, str, tuple[str, ...]]:
        """Identity used for comparison; the defaulting flag is provenance only."""
        return (self.regulation, self.kind, self.number, self.subs)

    def parent_key(self) -> tuple[str, str, str]:
        return (self.regulation, self.kind, self.number)

    def signature(self) -> tuple[str, str, tuple[str, ...]]:
        """Identity ignoring the regulation.

        Used for the exact-citation comparison. Most gold citations in this
        benchmark do not name their regulation, so requiring one would penalise
        a prediction for an omission the gold label shares.
        """
        return (self.kind, self.number, self.subs)

    def __str__(self) -> str:
        base = {
            "ARTICLE": f"Article {self.number}",
            "GM": f"GM {self.number}",
            "ANNEX": f"Annex {self.number}".strip(),
            "RECITALS": f"Recital {self.number}",
        }[self.kind]
        subs = "".join(f"({value})" for value in self.subs)
        return f"{base}{subs} [{self.regulation}]"


@dataclass
class ParentResolver:
    """Maps parsed citations onto parent identifiers that exist in the corpus."""

    parent_ids: set[str] = field(default_factory=set)

    @classmethod
    def from_parents(cls, parents: list[dict]) -> "ParentResolver":
        return cls(parent_ids={parent["parent_id"] for parent in parents})

    def resolve(self, citation: Citation) -> str | None:
        prefix = REGULATION_PREFIX.get(citation.regulation)
        if prefix is None:
            return None
        if citation.kind == "ARTICLE":
            candidate = f"{prefix}_ART_{citation.number}"
        elif citation.kind == "RECITALS":
            candidate = f"{prefix}_RECITALS"
        elif citation.kind == "GM":
            section = citation.number.replace(".", "_")
            candidate = f"GM_EU_376_2014_SEC_{section}"
        elif citation.kind == "ANNEX":
            candidate = (
                f"{prefix}_ANNEX_{citation.number.upper()}"
                if citation.number
                else f"{prefix}_ANNEX"
            )
        else:
            return None
        return candidate if candidate in self.parent_ids else None

    def resolve_candidates(self, citation: Citation) -> set[str]:
        """Every parent the citation could denote, given what it actually says.

        A citation that names its regulation denotes exactly one parent. A bare
        ``Article 2`` denotes any of the four regulations that have an Article 2,
        and this returns all of them. Scoring against the candidate set rather
        than against the default attribution means a prediction is never marked
        wrong for failing to make a distinction that the gold citation itself
        does not make.
        """
        if not citation.defaulted_regulation:
            parent = self.resolve(citation)
            return {parent} if parent else set()
        candidates = set()
        for regulation in REGULATION_PREFIX:
            parent = self.resolve(
                Citation(regulation, citation.kind, citation.number, citation.subs)
            )
            if parent:
                candidates.add(parent)
        return candidates

    def is_ambiguous(self, citation: Citation) -> bool:
        """True when the citation string alone cannot identify one provision."""
        return len(self.resolve_candidates(citation)) > 1

    def resolve_all(self, citations: list[Citation]) -> tuple[set[str], int]:
        """Return the resolvable parents and how many relied on the default."""
        parents: set[str] = set()
        defaulted = 0
        for citation in citations:
            parent = self.resolve(citation)
            if parent is None:
                continue
            parents.add(parent)
            if citation.defaulted_regulation:
                defaulted += 1
        return parents, defaulted


def _expand_range(values: list[str]) -> list[str]:
    """(11)-(12) means 11 and 12; letters and mixed runs are left as listed."""
    if len(values) != 2 or not all(value.isdigit() for value in values):
        return values
    start, end = int(values[0]), int(values[1])
    if not 0 < end - start < 30:
        return values
    return [str(value) for value in range(start, end + 1)]


def _regulation_at(text: str, position: int, window: int = 140) -> tuple[str, bool]:
    """Nearest regulation named before, else after, else the benchmark default."""
    before = text[max(0, position - window):position]
    matches = list(_REGULATION_PATTERN.finditer(before))
    if matches:
        return re.sub(r"\s+", "", matches[-1].group(1)), False
    after = text[position:position + window]
    match = _REGULATION_PATTERN.search(after)
    if match:
        return re.sub(r"\s+", "", match.group(1)), False
    return DEFAULT_REGULATION, True


def _parse_subs(tail: str) -> tuple[list[tuple[str, ...]], int]:
    """Parse the sub-paragraph run after an article number.

    Returns one sub-tuple per cited paragraph and how many characters were
    consumed. ``(1)(a)`` is one unit; ``(1), (2) and (3)`` is three.
    """
    paragraph = _PARAGRAPH_RUN.match(tail)
    if paragraph:
        numbers = re.findall(r"\d+", paragraph.group(1))
        if any(sep in paragraph.group(1) for sep in _RANGE_SEPARATORS):
            numbers = _expand_range(numbers)
        return [(number,) for number in numbers], paragraph.end()

    run = _SUB_RUN.match(tail)
    if not run:
        return [], 0
    segment = run.group(1)
    tokens = _SUB_TOKEN.findall(segment)
    if not tokens:
        return [], 0

    # Trim the consumed span at the last bracket so trailing "and"/"," is not eaten.
    consumed = segment.rfind(")") + 1

    groups: list[list[str]] = []
    cursor = 0
    for token in tokens:
        index = segment.index(f"({token}", cursor) if f"({token}" in segment[cursor:] else -1
        raw_gap = segment[cursor:index] if index >= 0 else ""
        cursor = (index + len(token) + 2) if index >= 0 else cursor
        # A letter immediately after a number, with no separator, refines it:
        # "(6)(a)" is one citation, "(1), (2)" is two.
        if groups and not raw_gap.strip(" ") and token.isalpha():
            groups[-1].append(token)
        else:
            groups.append([token])

    flat = [group[0] for group in groups]
    if len(groups) == 2 and all(len(group) == 1 for group in groups):
        if any(sep in segment for sep in _RANGE_SEPARATORS) and all(
            value.isdigit() for value in flat
        ):
            return [(value,) for value in _expand_range(flat)], consumed
    return [tuple(group) for group in groups], consumed


def parse_citations(text: str) -> list[Citation]:
    """Extract every atomic citation named in ``text``.

    The parser is deliberately literal: it recognises the citation forms that
    occur in this corpus and ignores everything else. It never guesses a
    sub-paragraph that was not written.
    """
    if not text:
        return []
    lowered = text.lower()
    found: list[Citation] = []

    consumed_to = 0
    for match in _ARTICLE_PATTERN.finditer(lowered):
        if match.start() < consumed_to:
            continue
        number = match.group(1) or match.group(2)
        regulation, defaulted = _regulation_at(lowered, match.start())
        plural = lowered[match.start():match.end()].lstrip().startswith("articles")

        def emit(article: str, groups: list[tuple[str, ...]]) -> None:
            for subs in groups or [()]:
                found.append(Citation(regulation, "ARTICLE", article, subs, defaulted))

        sub_groups, used = _parse_subs(lowered[match.end():])
        emit(number, sub_groups)
        cursor = match.end() + used

        # "and 7(8)" continues the enumeration. A bare number only continues it
        # when the citation opened with the plural "Articles", so that ordinary
        # prose like "Article 4 and 30 days" cannot yield an Article 30.
        while True:
            continuation = _CONTINUATION.match(lowered[cursor:])
            if not continuation:
                break
            next_number = continuation.group(1)
            next_groups, next_used = _parse_subs(lowered[cursor + continuation.end():])
            if not next_groups and not plural:
                break
            emit(next_number, next_groups)
            cursor += continuation.end() + next_used
        consumed_to = cursor

    for match in _GM_PATTERN.finditer(lowered):
        # Guidance material exists only for 376/2014 in this corpus.
        found.append(
            Citation("376/2014", "GM", f"{match.group(1)}.{match.group(2)}", (), False)
        )

    for match in _ANNEX_PATTERN.finditer(lowered):
        roman = (match.group(1) or "").upper()
        regulation, defaulted = _regulation_at(lowered, match.start())
        found.append(Citation(regulation, "ANNEX", roman, (), defaulted))

    for match in _RECITAL_PATTERN.finditer(lowered):
        regulation, defaulted = _regulation_at(lowered, match.start())
        found.append(Citation(regulation, "RECITALS", match.group(1), (), defaulted))

    unique: list[Citation] = []
    seen: set[tuple] = set()
    for citation in found:
        if citation.key() not in seen:
            seen.add(citation.key())
            unique.append(citation)
    return unique


def exact_citation_match(prediction: str, gold_citation: str) -> tuple[bool | None, list[str]]:
    """Is every atomic unit of the gold citation named in the prediction?

    Returns ``(None, [])`` when the gold citation contains no parseable unit --
    for instance ``GM to Reg. (EU) No 376/2014 [04]`` or a bare ``Paragraph 3``.
    Those records are excluded from the exact metric's denominator rather than
    silently scored zero, and their count is itself a finding: a citation label
    a parser cannot resolve is usually one a reader cannot resolve either.
    """
    gold_units = parse_citations(gold_citation)
    if not gold_units:
        return None, []
    predicted = {citation.signature() for citation in parse_citations(prediction)}
    missing = [str(unit) for unit in gold_units if unit.signature() not in predicted]
    return (not missing), missing


def parent_citation_match(
    prediction: str,
    gold_citation: str,
    resolver: ParentResolver,
) -> tuple[bool | None, dict]:
    """Does the prediction cite the provision(s) the gold citation denotes?

    Comparison is parent-level and citation-to-citation: both sides are put
    through the same parser and resolved against the corpus, so only parents
    that exist can be credited. Where the gold citation is ambiguous about its
    regulation, any candidate counts -- the benchmark's own label does not make
    that distinction, so the system is not penalised for reproducing it.

    Returns ``(None, ...)`` when the gold citation names no resolvable
    provision at all.
    """
    gold_units = parse_citations(gold_citation)
    gold_sets = [resolver.resolve_candidates(unit) for unit in gold_units]
    gold_sets = [candidates for candidates in gold_sets if candidates]
    detail = {
        "gold_parents": sorted(set().union(*gold_sets)) if gold_sets else [],
        "gold_ambiguous": any(len(candidates) > 1 for candidates in gold_sets),
        "predicted_parents": [],
        "missing_parents": [],
    }
    if not gold_sets:
        return None, detail

    predicted: set[str] = set()
    for unit in parse_citations(prediction):
        predicted |= resolver.resolve_candidates(unit)
    detail["predicted_parents"] = sorted(predicted)
    missing = [
        sorted(candidates) for candidates in gold_sets if not (candidates & predicted)
    ]
    detail["missing_parents"] = missing
    return (not missing), detail


def legacy_citation_match(prediction: str, gold_citation: str) -> float:
    """The original scorer, reproduced exactly, for continuity only.

    Retained so the re-scored results can be reported beside the numbers they
    replace. Never use this as a correctness measure.
    """
    if not gold_citation:
        return 0.0
    predicted = prediction.lower()
    gold = gold_citation.lower()
    if gold in predicted:
        return 1.0
    article = re.search(r"article\s+(\d+)", gold)
    if article and f"article {article.group(1)}" in predicted:
        return 0.5
    return 0.0
