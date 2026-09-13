"""WordprocessingML extraction with paragraph and table-row preservation."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG = "http://schemas.microsoft.com/office/2006/xmlPackage"
NS = {"w": W, "pkg": PKG}


@dataclass(frozen=True)
class ParagraphBlock:
    text: str
    style: str
    paragraph_index: int


@dataclass(frozen=True)
class TableRowBlock:
    cells: tuple[str, ...]
    headers: tuple[str, ...]
    is_header: bool
    table_index: int
    row_index: int
    paragraph_start: int | None
    paragraph_end: int | None


SourceBlock = ParagraphBlock | TableRowBlock


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def document_body(path: Path) -> ET.Element:
    """Load w:body from DOCX, Flat OPC, or standalone WordprocessingML."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            with archive.open("word/document.xml") as stream:
                root = ET.parse(stream).getroot()
        body = root.find("w:body", NS)
        if body is None:
            raise ValueError("DOCX does not contain w:body")
        return body

    root = ET.parse(path).getroot()
    if local_name(root.tag).lower() == "package":
        for part in root.findall("pkg:part", NS):
            if part.get(f"{{{PKG}}}name") != "/word/document.xml":
                continue
            xml_data = part.find("pkg:xmlData", NS)
            document = xml_data.find("w:document", NS) if xml_data is not None else None
            body = document.find("w:body", NS) if document is not None else None
            if body is not None:
                return body
        raise ValueError("Flat OPC package does not contain /word/document.xml")

    body = root.find(".//w:body", NS)
    if body is None:
        raise ValueError("XML does not contain w:body")
    return body


def paragraph_text(paragraph: ET.Element) -> str:
    return normalize_space("".join(node.text or "" for node in paragraph.findall(".//w:t", NS)))


def paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("w:pPr/w:pStyle", NS)
    if style is None:
        return ""
    return style.get(f"{{{W}}}val") or style.get("val") or ""


def _cell_text(cell: ET.Element) -> str:
    parts = [paragraph_text(p) for p in cell.findall(".//w:p", NS)]
    return normalize_space(" ".join(part for part in parts if part))


def _vertical_merge(cell: ET.Element) -> str | None:
    merge = cell.find("w:tcPr/w:vMerge", NS)
    if merge is None:
        return None
    value = merge.get(f"{{{W}}}val") or merge.get("val")
    return value or "continue"




def iter_source_blocks(path: Path) -> list[SourceBlock]:
    """Return body-level paragraphs and table rows in document order."""
    body = document_body(path)
    all_paragraphs = list(body.findall(".//w:p", NS))
    paragraph_indexes = {id(paragraph): index for index, paragraph in enumerate(all_paragraphs)}
    blocks: list[SourceBlock] = []
    table_index = 0

    def structural_elements(element: ET.Element):
        """Yield paragraphs/tables in order without yielding table paragraphs twice."""
        for child in element:
            kind = local_name(child.tag)
            if kind in {"p", "tbl"}:
                yield child
            else:
                yield from structural_elements(child)

    for element in structural_elements(body):
        kind = local_name(element.tag)
        if kind == "p":
            text = paragraph_text(element)
            if text:
                blocks.append(
                    ParagraphBlock(
                        text=text,
                        style=paragraph_style(element),
                        paragraph_index=paragraph_indexes[id(element)],
                    )
                )
            continue

        if kind != "tbl":
            continue

        rows = element.findall("w:tr", NS)
        parsed_rows: list[tuple[tuple[str, ...], list[ET.Element], bool]] = []
        vertical_values: dict[int, str] = {}
        for row in rows:
            cell_values: list[str] = []
            for column_index, cell in enumerate(row.findall("w:tc", NS)):
                text = _cell_text(cell)
                merge = _vertical_merge(cell)
                if merge == "restart":
                    vertical_values[column_index] = text
                elif merge == "continue":
                    text = text or vertical_values.get(column_index, "")
                else:
                    vertical_values.pop(column_index, None)
                cell_values.append(text)
            cells = tuple(cell_values)
            paragraphs = row.findall(".//w:p", NS)
            is_header = any(paragraph_style(p) == "TableHead" for p in paragraphs)
            parsed_rows.append((cells, paragraphs, is_header))

        header_index = next(
            (index for index, (_, _, is_header) in enumerate(parsed_rows) if is_header),
            None,
        )
        header_row = parsed_rows[header_index][0] if header_index is not None else tuple()
        if header_index is None and len(parsed_rows) > 1:
            first_cells = parsed_rows[0][0]
            if first_cells and all(first_cells):
                header_index = 0
                header_row = first_cells

        for row_index, (cells, paragraphs, explicit_header) in enumerate(parsed_rows):
            nonempty = tuple(cell for cell in cells if cell)
            if not nonempty:
                continue
            indexes = [paragraph_indexes[id(p)] for p in paragraphs if id(p) in paragraph_indexes]
            blocks.append(
                TableRowBlock(
                    cells=cells,
                    headers=header_row,
                    is_header=explicit_header or row_index == header_index,
                    table_index=table_index,
                    row_index=row_index,
                    paragraph_start=min(indexes) if indexes else None,
                    paragraph_end=max(indexes) if indexes else None,
                )
            )
        table_index += 1

    return blocks

