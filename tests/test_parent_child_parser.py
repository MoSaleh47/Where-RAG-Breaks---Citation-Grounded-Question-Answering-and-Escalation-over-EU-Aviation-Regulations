from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.corpus import build_parent_child_corpus  # noqa: E402
from aviation_rag.corpus.validation import validate_corpus  # noqa: E402

SOURCE = (
    WORKSPACE_ROOT
    / "Documents"
    / "03C2C2_2023-09-27_09.31.20_EAR-for-Occurrence-Reporting-Regulation-EU-No-376-2014.xml"
)


def corpus():
    return build_parent_child_corpus(SOURCE)


def test_no_critical_validation_issues():
    issues, summary = validate_corpus(corpus())
    assert summary["critical_issue_count"] == 0, [issue for issue in issues if issue.severity == "critical"]
    assert summary["warning_issue_count"] == 0, [issue for issue in issues if issue.severity == "warning"]


def test_distinct_regulations_have_distinct_article_ids():
    records = corpus().parents
    article_1_ids = {
        parent.parent_id
        for parent in records
        if parent.document_type == "ARTICLE" and parent.canonical_citation == "Article 1"
    }
    assert article_1_ids == {
        "EU_376_2014_ART_1",
        "EU_2015_1018_ART_1",
        "EU_2020_2034_ART_1",
        "EU_2021_2082_ART_1",
    }


def test_guidance_paragraphs_are_not_articles():
    records = corpus().parents
    gm = next(parent for parent in records if parent.parent_id == "GM_EU_376_2014_SEC_1_6")
    assert gm.document_type == "GM"
    assert "Article 4(7) requests reporters" in gm.text
    assert not any(
        parent.document_type == "ARTICLE" and "Article 4(7) requests reporters" in parent.title
        for parent in records
    )


def test_article_4_has_paragraph_level_children_and_citations():
    records = corpus()
    article = next(parent for parent in records.parents if parent.parent_id == "EU_376_2014_ART_4")
    children = [child for child in records.children if child.parent_id == article.parent_id]
    assert len(children) > 20
    assert any(child.canonical_citation == "Article 4(7)" for child in children)
    assert any(child.canonical_citation == "Article 4(6)(a)" for child in children)
    assert any(child.canonical_citation == "Article 4(1)(a)(i)" for child in children)
    assert not any(child.canonical_citation == "Article 4(1)(i)(ii)" for child in children)
    assert max(child.char_count for child in children) < article.char_count


def test_annex_tables_are_preserved_as_rows():
    records = corpus()
    table_children = [child for child in records.children if child.unit_type == "table_row"]
    assert len(table_children) > 100
    assert all(child.source_location["table_index"] is not None for child in table_children)


def test_table_headers_are_typed_separately():
    records = corpus()
    headers = [child for child in records.children if child.unit_type == "table_header"]
    assert len(headers) >= 8
    assert all(child.source_location["table_index"] is not None for child in headers)


def test_vertically_merged_table_context_is_forward_filled():
    records = corpus()
    assert any(
        child.unit_type == "table_row"
        and "KEY RISK AREA: Airborne collision" in child.text
        and "CATEGORY: Between 20 to 100 possible fatalities" in child.text
        for child in records.children
    )


def test_single_cell_layout_tables_are_callouts():
    records = corpus()
    callouts = [child for child in records.children if child.unit_type == "callout"]
    assert len(callouts) > 50
    assert any("Key principle" in child.text for child in callouts)


def test_all_regulations_retain_recitals():
    recital_documents = {
        parent.document_id for parent in corpus().parents if parent.document_type == "RECITALS"
    }
    assert recital_documents == {
        "EU_376_2014",
        "EU_2015_1018",
        "EU_2020_2034",
        "EU_2021_2082",
    }


def test_unnumbered_annex_ids_are_short_and_canonical():
    annex_ids = {
        parent.parent_id
        for parent in corpus().parents
        if parent.document_type == "ANNEX" and parent.canonical_citation == "Annex"
    }
    assert annex_ids == {"EU_2020_2034_ANNEX", "EU_2021_2082_ANNEX"}


def test_acronyms_are_not_attached_to_the_last_guidance_question():
    records = corpus()
    acronyms = next(
        parent for parent in records.parents if parent.parent_id == "GM_EU_376_2014_ACRONYMS"
    )
    last_question = next(
        parent for parent in records.parents if parent.parent_id == "GM_EU_376_2014_SEC_5_10"
    )
    assert "ATM/ANS" in acronyms.text
    assert "LIST OF ACRONYMS" not in last_question.text


def test_parent_and_child_ids_are_unique_and_referentially_valid():
    records = corpus()
    parent_ids = {parent.parent_id for parent in records.parents}
    child_ids = [child.child_id for child in records.children]
    assert len(parent_ids) == len(records.parents)
    assert len(child_ids) == len(set(child_ids))
    assert all(child.parent_id in parent_ids for child in records.children)

