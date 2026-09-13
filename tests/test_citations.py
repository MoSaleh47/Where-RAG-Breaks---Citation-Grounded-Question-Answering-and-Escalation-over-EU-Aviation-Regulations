"""Tests for citation parsing and parent resolution.

The cases are taken from the gold citations that actually occur in the frozen
benchmark and from the failure modes of the scorer this module replaces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aviation_rag.evaluation.citations import (
    Citation,
    ParentResolver,
    exact_citation_match,
    legacy_citation_match,
    parent_citation_match,
    parse_citations,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARENTS = PROJECT_ROOT / "data/processed/E1_parent_child_v1/parents.jsonl"


def keys(text: str) -> set[tuple]:
    return {citation.key() for citation in parse_citations(text)}


# --- the defects that motivated the rewrite ---------------------------------


def test_article_does_not_match_its_own_subparagraph():
    assert exact_citation_match("see Article 4(6)", "Article 4")[0] is False
    assert exact_citation_match("see Article 4", "Article 4(6)")[0] is False


def test_legacy_scorer_gets_both_of_those_wrong():
    """Documents the behaviour being replaced, so the change is auditable."""
    assert legacy_citation_match("see Article 4(6)", "Article 4") == 1.0
    assert legacy_citation_match("see Article 4", "Article 4(6)") == 0.5


def test_naming_the_article_alone_is_not_exact_credit():
    supported, missing = exact_citation_match(
        "This is governed by Article 16 of the Regulation.", "Article 16(6)"
    )
    assert supported is False and missing


# --- parsing ----------------------------------------------------------------


def test_simple_article_with_paragraph():
    assert Citation("376/2014", "ARTICLE", "4", ("1",), True).key() in keys("Article 4(1)")


def test_letter_refines_the_paragraph_rather_than_adding_one():
    parsed = parse_citations("Article 4(6)(a)")
    assert len(parsed) == 1
    assert parsed[0].subs == ("6", "a")


def test_comma_list_expands_to_one_unit_per_paragraph():
    parsed = keys("Article 16(1), (2) and (3)")
    assert {citation[3] for citation in parsed} == {("1",), ("2",), ("3",)}


def test_range_expands_inclusively():
    assert {citation[3] for citation in keys("Article 16(11)-(12)")} == {("11",), ("12",)}
    assert {citation[3] for citation in keys("Article 5(1)-(2)")} == {("1",), ("2",)}


def test_paragraph_wording_is_equivalent_to_brackets():
    assert keys("Article 13, paragraph 1") == keys("Article 13(1)")
    assert keys("Article 13, paragraphs 4 and 5") == keys("Article 13(4), (5)")


def test_guidance_material_and_recitals():
    assert Citation("376/2014", "GM", "3.1").key() in keys("see GM 3.1")
    assert Citation("376/2014", "RECITALS", "35", (), True).key() in keys("Recital 35")


def test_named_regulation_overrides_the_default():
    parsed = parse_citations("Regulation 2015/1018, Annex V")
    assert any(c.regulation == "2015/1018" and c.kind == "ANNEX" for c in parsed)
    assert all(not c.defaulted_regulation for c in parsed if c.kind == "ANNEX")


def test_unnamed_regulation_defaults_and_is_flagged():
    parsed = parse_citations("under Article 6(1)")
    assert parsed[0].regulation == "376/2014"
    assert parsed[0].defaulted_regulation is True


def test_no_citation_yields_nothing():
    assert parse_citations("The operator must report the occurrence promptly.") == []
    assert parse_citations("") == []


# --- gold citations the parser cannot resolve -------------------------------


@pytest.mark.parametrize(
    "gold",
    [
        "GM to Reg. (EU) No 376/2014 [04]",
        "GM to Reg. (EU) No 376/2014 and its IRs [05]",
        "Paragraph 3",
        "GM to Reg. (EU) No 376/2014, Section ii",
    ],
)
def test_unparseable_gold_is_undefined_not_zero(gold):
    """These are the citation labels a practitioner could not read either."""
    supported, _ = exact_citation_match("Article 4(6) applies.", gold)
    assert supported is None


# --- resolution against the corpus ------------------------------------------


@pytest.fixture(scope="module")
def resolver() -> ParentResolver:
    parents = [
        json.loads(line)
        for line in PARENTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return ParentResolver.from_parents(parents)


def test_resolution_targets_real_parents(resolver):
    assert resolver.resolve(Citation("376/2014", "ARTICLE", "4")) == "EU_376_2014_ART_4"
    assert resolver.resolve(Citation("376/2014", "GM", "3.1")) == "GM_EU_376_2014_SEC_3_1"
    assert resolver.resolve(Citation("2015/1018", "ANNEX", "V")) == "EU_2015_1018_ANNEX_V"
    assert resolver.resolve(Citation("376/2014", "RECITALS", "35")) == "EU_376_2014_RECITALS"


def test_subparagraph_does_not_change_the_parent(resolver):
    with_sub = resolver.resolve(Citation("376/2014", "ARTICLE", "4", ("6", "a")))
    assert with_sub == resolver.resolve(Citation("376/2014", "ARTICLE", "4"))


def test_article_absent_from_a_regulation_does_not_resolve(resolver):
    # 2021/2082 stops at Article 6; 376/2014 has an Article 24.
    assert resolver.resolve(Citation("2021/2082", "ARTICLE", "24")) is None
    assert resolver.resolve(Citation("376/2014", "ARTICLE", "24")) == "EU_376_2014_ART_24"


def test_invented_reference_resolves_to_nothing(resolver):
    assert resolver.resolve(Citation("376/2014", "ARTICLE", "97")) is None


def test_resolve_all_counts_defaulted_attributions(resolver):
    parents, defaulted = resolver.resolve_all(parse_citations("Article 4 and Article 7"))
    assert parents == {"EU_376_2014_ART_4", "EU_376_2014_ART_7"}
    assert defaulted == 2
    parents, defaulted = resolver.resolve_all(
        parse_citations("Article 4 of Regulation (EU) No 376/2014")
    )
    assert parents == {"EU_376_2014_ART_4"} and defaulted == 0


def test_ambiguous_gold_yields_every_candidate_regulation(resolver):
    """A bare "Article 2" exists in four regulations and must not be forced to one."""
    unit = parse_citations("Article 2")[0]
    assert resolver.is_ambiguous(unit)
    assert resolver.resolve_candidates(unit) == {
        "EU_376_2014_ART_2",
        "EU_2015_1018_ART_2",
        "EU_2020_2034_ART_2",
        "EU_2021_2082_ART_2",
    }


def test_named_regulation_is_not_ambiguous(resolver):
    unit = parse_citations("Article 2 of Regulation (EU) 2015/1018")[0]
    assert not resolver.is_ambiguous(unit)
    assert resolver.resolve_candidates(unit) == {"EU_2015_1018_ART_2"}


def test_parent_match_credits_the_right_provision(resolver):
    supported, detail = parent_citation_match(
        "This follows from Article 4(6)(b).", "Article 4(6)(b)", resolver
    )
    assert supported is True
    # The prediction does not name a regulation, so every Article 4 in the corpus
    # is a candidate; the benchmark's own label is equally unspecific.
    assert "EU_376_2014_ART_4" in detail["predicted_parents"]
    assert detail["gold_ambiguous"] is True


def test_parent_match_rejects_a_different_article(resolver):
    supported, detail = parent_citation_match(
        "This follows from Article 7.", "Article 4(6)(b)", resolver
    )
    assert supported is False
    assert detail["missing_parents"]


def test_parent_match_requires_every_gold_provision(resolver):
    supported, _ = parent_citation_match(
        "See Article 9(1).", "Article 9(1), Article 13(9)", resolver
    )
    assert supported is False


def test_parent_match_is_undefined_for_unresolvable_gold(resolver):
    supported, _ = parent_citation_match(
        "See Article 4.", "GM to Reg. (EU) No 376/2014 [04]", resolver
    )
    assert supported is None


def test_exact_match_ignores_the_regulation_but_not_the_paragraph(resolver):
    assert exact_citation_match("Article 5(2) of Regulation (EU) 2021/2082", "Article 5(2)")[0]
    assert exact_citation_match("Article 5 of Regulation (EU) 2021/2082", "Article 5(2)")[0] is False


def test_benchmark_citation_labels_are_measurably_underspecified(resolver):
    """Guards the Chapter 5 claim: most gold labels do not name their own parent.

    This is a property of the benchmark, not a parser defect, so it is asserted
    rather than fixed. Three distinct causes, counted separately:
      * the citation names an Article while the evidence sits in a GM section;
      * the citation omits which of the four regulations it means;
      * the citation cannot be parsed into any provision at all.
    """
    benchmark = PROJECT_ROOT / "data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl"
    records = [
        json.loads(line)
        for line in benchmark.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 98

    identifies_own_parent = guidance_indirection = ambiguous = unparseable = 0
    for record in records:
        units = parse_citations(record["acceptable_citation"])
        if not units:
            unparseable += 1
            continue
        parents, _ = resolver.resolve_all(units)
        if record["parent_id"] in parents:
            identifies_own_parent += 1
        elif record["parent_id"].startswith("GM_"):
            guidance_indirection += 1
        elif any(resolver.is_ambiguous(unit) for unit in units):
            ambiguous += 1
        else:
            raise AssertionError(f"unclassified citation on {record['qa_id']}")

    assert identifies_own_parent == 48
    assert guidance_indirection == 28
    assert ambiguous == 12
    assert unparseable == 10
    # 22 of 98 records carry a label no reader can resolve to one provision.
    assert ambiguous + unparseable == 22
