"""Deterministic hierarchy-aware parent/child corpus builder."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .wordml import ParagraphBlock, SourceBlock, TableRowBlock, iter_source_blocks, normalize_space

DOCUMENT_HEADINGS = {
    "Regulation (EU) No 376/2014": ("EU_376_2014", "EU 376/2014", "REGULATION"),
    "Commission Implementing Regulation (EU) 2015/1018": (
        "EU_2015_1018",
        "EU 2015/1018",
        "IMPLEMENTING_REGULATION",
    ),
    "Commission Delegated Regulation (EU) 2020/2034": (
        "EU_2020_2034",
        "EU 2020/2034",
        "DELEGATED_REGULATION",
    ),
    "Commission Implementing Regulation (EU) 2021/2082": (
        "EU_2021_2082",
        "EU 2021/2082",
        "IMPLEMENTING_REGULATION",
    ),
    "Guidance Material — Regulation (EU) No 376/2014 and its implementing rules": (
        "GM_EU_376_2014",
        "EU 376/2014 and implementing rules",
        "GUIDANCE_MATERIAL",
    ),
}

SKIP_CONTENT_STYLES = {"Dxshortdesc", "AlignRight"}


@dataclass
class Child:
    child_id: str
    parent_id: str
    sequence: int
    canonical_citation: str
    unit_type: str
    text: str
    retrieval_text: str
    char_count: int
    word_count: int
    source_location: dict[str, int | None]
    marker_path: list[str] = field(default_factory=list)


@dataclass
class Parent:
    parent_id: str
    document_id: str
    document_version: str
    regulation_id: str
    regulation_kind: str
    document_type: str
    hierarchy_path: list[str]
    canonical_citation: str
    title: str
    formal_title: str
    text: str
    char_count: int
    word_count: int
    child_ids: list[str]
    source_location: dict[str, int | None]
    cross_references: list[str]


@dataclass
class Corpus:
    parents: list[Parent]
    children: list[Child]
    ignored_blocks: int

    def parents_as_dicts(self) -> list[dict]:
        return [asdict(parent) for parent in self.parents]

    def children_as_dicts(self) -> list[dict]:
        return [asdict(child) for child in self.children]


@dataclass
class _DocumentState:
    document_id: str = ""
    regulation_id: str = ""
    regulation_kind: str = ""
    formal_title: str = ""
    section_title: str = ""


@dataclass
class _ParentBuilder:
    parent_id: str
    document_id: str
    document_version: str
    regulation_id: str
    regulation_kind: str
    document_type: str
    hierarchy_path: list[str]
    canonical_citation: str
    title: str
    formal_title: str
    paragraph_start: int | None
    paragraph_end: int | None
    children: list[Child] = field(default_factory=list)
    marker_path: list[str] = field(default_factory=list)


def _slug(value: str) -> str:
    ascii_value = value.upper().replace("—", " ").replace("–", " ")
    return re.sub(r"[^A-Z0-9]+", "_", ascii_value).strip("_")


def _short_digest(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8].upper()


def _article_number(title: str) -> str | None:
    match = re.match(r"Article\s+(\d+[A-Za-z]?)\b", title, re.IGNORECASE)
    return match.group(1) if match else None


def _annex_label(title: str, section_title: str) -> str:
    match = re.match(r"ANNEX\s+([IVXLCDM]+)\b", title, re.IGNORECASE)
    if match:
        return f"Annex {match.group(1).upper()}"
    if section_title.upper().startswith("ANNEX"):
        return "Annex"
    return "Annex section"


def _gm_number(title: str) -> str | None:
    match = re.match(r"(\d+(?:\.\d+)+)", title)
    return match.group(1) if match else None


def _parent_identity(
    document_id: str,
    document_type: str,
    title: str,
    section_title: str,
) -> tuple[str, str]:
    if document_type == "ARTICLE":
        number = _article_number(title)
        if number:
            return f"{document_id}_ART_{_slug(number)}", f"Article {number}"
    if document_type == "ANNEX":
        label = _annex_label(title, section_title)
        if label == "Annex":
            return f"{document_id}_ANNEX", label
        return f"{document_id}_{_slug(label)}", label
    if document_type == "GM":
        if title.upper() == "LIST OF ACRONYMS":
            return f"{document_id}_ACRONYMS", "GM acronyms"
        number = _gm_number(title)
        if number:
            return f"{document_id}_SEC_{number.replace('.', '_')}", f"GM {number}"
    if document_type == "RECITALS":
        return f"{document_id}_RECITALS", "Powers and recitals"
    suffix = _slug(title)[:60] or _short_digest(title)
    return f"{document_id}_{suffix}", title


def _extract_cross_references(text: str) -> list[str]:
    references: set[str] = set()
    for match in re.finditer(
        r"\bArticle\s+(\d+[A-Za-z]?)(?:\((\d+)\))?(?:\(([a-z])\))?",
        text,
        re.IGNORECASE,
    ):
        citation = f"Article {match.group(1)}"
        if match.group(2):
            citation += f"({match.group(2)})"
        if match.group(3):
            citation += f"({match.group(3).lower()})"
        references.add(citation)
    return sorted(references)


def _marker(text: str) -> tuple[str | None, str | None]:
    patterns = (
        ("decimal", r"^(\d+(?:\.\d+)*)[.\s]"),
        ("parenthesized_number", r"^\((\d+)\)"),
        ("letter", r"^\(([a-z])\)"),
        ("roman", r"^\(([ivxlcdm]+)\)"),
    )
    for kind, pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return kind, match.group(1).lower()
    return None, None


def _update_marker_path(
    current: list[str], text: str, style: str, document_type: str
) -> list[str]:
    kind, value = _marker(text)
    if value is None:
        return current

    if document_type == "ARTICLE":
        if style == "ListLevel0" and kind in {"decimal", "parenthesized_number"}:
            return [value.split(".")[0]]
        if style == "ListLevel1":
            return current[:1] + [value]
        if style == "ListLevel2":
            return current[:2] + [value]

    if document_type == "ANNEX":
        if kind == "decimal":
            return value.split(".")
        if style == "ListLevel1":
            return current[:1] + [value]
        if style == "ListLevel2":
            return current[:2] + [value]
        if kind == "parenthesized_number":
            return current + [value]

    if kind == "decimal":
        return value.split(".")
    return current + [value]


def _child_citation(parent: _ParentBuilder, marker_path: list[str]) -> str:
    if parent.document_type == "ARTICLE" and marker_path:
        return parent.canonical_citation + "".join(f"({part})" for part in marker_path)
    if parent.document_type == "ANNEX" and marker_path:
        return f"{parent.canonical_citation}, item {'.'.join(marker_path)}"
    return parent.canonical_citation


def _ancestor_context(parent: _ParentBuilder, marker_path: list[str]) -> str:
    ancestors: list[str] = []
    for depth in range(1, len(marker_path)):
        prefix = marker_path[:depth]
        ancestor = next(
            (child for child in reversed(parent.children) if child.marker_path == prefix),
            None,
        )
        if ancestor is not None:
            ancestors.append(ancestor.text)
    return " ".join(ancestors)


def _retrieval_text(
    parent: _ParentBuilder, citation: str, text: str, governing_text: str = ""
) -> str:
    hierarchy = " > ".join(part for part in parent.hierarchy_path[1:] if part)
    context = f" Governing text: {governing_text}." if governing_text else ""
    return normalize_space(
        f"Document: {parent.regulation_id}. Type: {parent.document_type}. "
        f"Hierarchy: {hierarchy}. Citation: {citation}.{context} Evidence: {text}"
    )


def _table_text(block: TableRowBlock) -> str:
    parts: list[str] = []
    for index, cell in enumerate(block.cells):
        if not cell:
            continue
        header = block.headers[index] if index < len(block.headers) and block.headers[index] else None
        parts.append(f"{header}: {cell}" if header and header != cell else cell)
    return " | ".join(parts)


def _add_child(parent: _ParentBuilder, block: SourceBlock) -> None:
    if isinstance(block, ParagraphBlock):
        if block.style in SKIP_CONTENT_STYLES:
            return
        text = block.text
        parent.marker_path = _update_marker_path(
            parent.marker_path, text, block.style, parent.document_type
        )
        unit_type = "list_item" if block.style.startswith("List") or block.style.startswith("bullet") else "paragraph"
        source_location = {
            "xml_paragraph_start": block.paragraph_index,
            "xml_paragraph_end": block.paragraph_index,
            "table_index": None,
            "table_row_index": None,
        }
    else:
        text = _table_text(block)
        if not text:
            return
        if block.is_header:
            unit_type = "table_header"
        elif sum(bool(cell) for cell in block.cells) > 1:
            unit_type = "table_row"
        else:
            unit_type = "callout"
        source_location = {
            "xml_paragraph_start": block.paragraph_start,
            "xml_paragraph_end": block.paragraph_end,
            "table_index": block.table_index,
            "table_row_index": block.row_index,
        }

    sequence = len(parent.children) + 1
    child_id = f"{parent.parent_id}__C{sequence:04d}"
    citation = _child_citation(parent, parent.marker_path)
    governing_text = _ancestor_context(parent, parent.marker_path)
    parent.children.append(
        Child(
            child_id=child_id,
            parent_id=parent.parent_id,
            sequence=sequence,
            canonical_citation=citation,
            unit_type=unit_type,
            text=text,
            retrieval_text=_retrieval_text(parent, citation, text, governing_text),
            char_count=len(text),
            word_count=len(text.split()),
            source_location=source_location,
            marker_path=list(parent.marker_path),
        )
    )
    end = source_location["xml_paragraph_end"]
    if end is not None:
        parent.paragraph_end = end


def _finish_parent(builder: _ParentBuilder | None) -> Parent | None:
    if builder is None or not builder.children:
        return None
    text = "\n".join(child.text for child in builder.children)
    references = set(_extract_cross_references(text))
    references.discard(builder.canonical_citation)
    return Parent(
        parent_id=builder.parent_id,
        document_id=builder.document_id,
        document_version=builder.document_version,
        regulation_id=builder.regulation_id,
        regulation_kind=builder.regulation_kind,
        document_type=builder.document_type,
        hierarchy_path=builder.hierarchy_path,
        canonical_citation=builder.canonical_citation,
        title=builder.title,
        formal_title=builder.formal_title,
        text=text,
        char_count=len(text),
        word_count=len(text.split()),
        child_ids=[child.child_id for child in builder.children],
        source_location={
            "xml_paragraph_start": builder.paragraph_start,
            "xml_paragraph_end": builder.paragraph_end,
        },
        cross_references=sorted(references),
    )


def build_parent_child_corpus(source: Path, document_version: str = "2022-12") -> Corpus:
    blocks = iter_source_blocks(source)
    state = _DocumentState()
    parent_builder: _ParentBuilder | None = None
    parents: list[Parent] = []
    children: list[Child] = []
    used_parent_ids: set[str] = set()
    ignored_blocks = 0

    def close_parent() -> None:
        nonlocal parent_builder
        parent = _finish_parent(parent_builder)
        if parent is not None:
            parents.append(parent)
            children.extend(parent_builder.children)
        parent_builder = None

    for block in blocks:
        if isinstance(block, TableRowBlock):
            if parent_builder is None:
                ignored_blocks += 1
            else:
                _add_child(parent_builder, block)
            continue

        text, style = block.text, block.style
        if style == "Heading1" and text in DOCUMENT_HEADINGS:
            close_parent()
            document_id, regulation_id, regulation_kind = DOCUMENT_HEADINGS[text]
            state = _DocumentState(
                document_id=document_id,
                regulation_id=regulation_id,
                regulation_kind=regulation_kind,
                formal_title=text,
            )
            continue

        if not state.document_id:
            ignored_blocks += 1
            continue

        if style == "Formaltitle":
            state.formal_title = text
            continue

        if style == "Heading2":
            close_parent()
            state.section_title = text
            continue

        parent_type: str | None = None
        if style == "Heading3CR":
            parent_type = "RECITALS" if text.lower() == "powers and recitals" else "ARTICLE"
        elif style == "Heading3IR":
            parent_type = "ANNEX"
        elif style == "Heading3GM":
            parent_type = "GM"
        elif style == "Heading2GM" and text.upper() == "LIST OF ACRONYMS":
            parent_type = "GM"

        if parent_type is not None:
            close_parent()
            parent_id, citation = _parent_identity(
                state.document_id,
                parent_type,
                text,
                state.section_title,
            )
            if parent_id in used_parent_ids:
                parent_id = f"{parent_id}_{_short_digest(text + str(block.paragraph_index))}"
            used_parent_ids.add(parent_id)
            parent_builder = _ParentBuilder(
                parent_id=parent_id,
                document_id=state.document_id,
                document_version=document_version,
                regulation_id=state.regulation_id,
                regulation_kind=state.regulation_kind,
                document_type=parent_type,
                hierarchy_path=[state.formal_title, state.section_title, text],
                canonical_citation=citation,
                title=text,
                formal_title=state.formal_title,
                paragraph_start=block.paragraph_index,
                paragraph_end=block.paragraph_index,
            )
            continue

        if parent_builder is None:
            is_cover_regulation = state.section_title.lower() == "cover regulation"
            if is_cover_regulation and state.regulation_kind != "GUIDANCE_MATERIAL":
                parent_id, citation = _parent_identity(
                    state.document_id,
                    "RECITALS",
                    "Powers and recitals",
                    state.section_title,
                )
                if parent_id in used_parent_ids:
                    parent_id = f"{parent_id}_{_short_digest(text + str(block.paragraph_index))}"
                used_parent_ids.add(parent_id)
                parent_builder = _ParentBuilder(
                    parent_id=parent_id,
                    document_id=state.document_id,
                    document_version=document_version,
                    regulation_id=state.regulation_id,
                    regulation_kind=state.regulation_kind,
                    document_type="RECITALS",
                    hierarchy_path=[
                        state.formal_title,
                        state.section_title,
                        "Powers and recitals",
                    ],
                    canonical_citation=citation,
                    title="Powers and recitals",
                    formal_title=state.formal_title,
                    paragraph_start=block.paragraph_index,
                    paragraph_end=block.paragraph_index,
                )
                _add_child(parent_builder, block)
            else:
                ignored_blocks += 1
        else:
            _add_child(parent_builder, block)

    close_parent()
    return Corpus(parents=parents, children=children, ignored_blocks=ignored_blocks)

