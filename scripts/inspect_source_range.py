"""Print selected paragraph ranges from the source XML for parser development."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_source_xml import NS, document_body, paragraph_style, paragraph_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("ranges", nargs="+", help="Inclusive ranges such as 300:340")
    args = parser.parse_args()

    paragraphs = list(document_body(args.source).findall(".//w:p", NS))
    for range_text in args.ranges:
        start_text, end_text = range_text.split(":", 1)
        start, end = int(start_text), int(end_text)
        print(f"\nRANGE {start}:{end}")
        for index in range(start, min(end + 1, len(paragraphs))):
            paragraph = paragraphs[index]
            text = paragraph_text(paragraph)
            if text:
                print(f"{index:04d} [{paragraph_style(paragraph)}] {text}")


if __name__ == "__main__":
    main()
