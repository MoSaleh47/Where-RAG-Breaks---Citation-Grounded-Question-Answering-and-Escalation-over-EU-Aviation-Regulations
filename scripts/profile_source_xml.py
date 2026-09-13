"""Profile the source WordprocessingML structure without modifying project data."""

from __future__ import annotations

import argparse
import collections
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG = "http://schemas.microsoft.com/office/2006/xmlPackage"
NS = {"w": W, "pkg": PKG}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def document_body(path: Path) -> ET.Element:
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
    text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))
    return re.sub(r"\s+", " ", text).strip()


def paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("w:pPr/w:pStyle", NS)
    if style is None:
        return "<none>"
    return style.get(f"{{{W}}}val") or style.get("val") or "<none>"


def profile(path: Path, sample_limit: int) -> None:
    body = document_body(path)
    paragraphs = list(body.findall(".//w:p", NS))
    tables = list(body.findall(".//w:tbl", NS))

    style_counts: collections.Counter[str] = collections.Counter()
    style_samples: dict[str, list[str]] = collections.defaultdict(list)
    article_candidates: list[tuple[int, str, str]] = []
    annex_candidates: list[tuple[int, str, str]] = []
    gm_candidates: list[tuple[int, str, str]] = []
    numeric_candidates: list[tuple[int, str, str]] = []

    for index, paragraph in enumerate(paragraphs):
        text = paragraph_text(paragraph)
        if not text:
            continue
        style = paragraph_style(paragraph)
        style_counts[style] += 1
        if len(style_samples[style]) < sample_limit:
            style_samples[style].append(text[:220])

        row = (index, style, text[:300])
        if re.match(r"^Article\s*\d+", text, re.IGNORECASE):
            article_candidates.append(row)
        if re.match(r"^Annex\b", text, re.IGNORECASE):
            annex_candidates.append(row)
        if re.match(r"^(GM\b|Guidance Material\b)", text, re.IGNORECASE):
            gm_candidates.append(row)
        if re.match(r"^\d+(?:\.\d+)+\s+\S", text) and len(text) < 240:
            numeric_candidates.append(row)

    print(f"source={path}")
    print(f"paragraphs={len(paragraphs)}")
    print(f"tables={len(tables)}")
    print(f"table_rows={len(body.findall('.//w:tr', NS))}")
    print(f"nonempty_paragraphs={sum(style_counts.values())}")

    print("\nSTYLE DISTRIBUTION")
    for style, count in style_counts.most_common():
        print(f"\n[{style}] count={count}")
        for sample in style_samples[style]:
            print(f"  - {sample}")

    for label, candidates in (
        ("ARTICLE PREFIX CANDIDATES", article_candidates),
        ("ANNEX PREFIX CANDIDATES", annex_candidates),
        ("GM PREFIX CANDIDATES", gm_candidates),
        ("NUMERIC SECTION CANDIDATES", numeric_candidates),
    ):
        print(f"\n{label} count={len(candidates)}")
        for index, style, text in candidates:
            print(f"  {index:04d} [{style}] {text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--sample-limit", type=int, default=4)
    args = parser.parse_args()
    profile(args.source, args.sample_limit)


if __name__ == "__main__":
    main()
