#!/usr/bin/env python3
"""
clean_bib.py — 清洗 BibTeX 条目，只保留 bib-arxiv-daily 项目实际使用的字段。

保留的字段：
  - title        (必须，用于推荐和去重)
  - abstract     (必须，用于嵌入相似度计算)
  - author       (可选，报告中显示作者)
  - doi          (可选，用于去重 canonical_identity)
  - eprint       (可选，用于提取 arxiv_id 去重)
  - archiveprefix(可选，辅助提取 arxiv_id)
  - url          (可选，辅助提取 arxiv_id + 报告中显示链接)

用法：
  python scripts/clean_bib.py data/library.bib               # 原地替换（建议先备份）
  python scripts/clean_bib.py data/library.bib -o output.bib  # 输出到新文件
  python scripts/clean_bib.py data/*.bib                      # 批量处理

注意：
  - 不会删除条目，只删除多余字段。
  - 条目若缺失 title 或 abstract 会被保留但标记警告。
  - 原始文件建议先 git commit 或备份。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


KEEP_FIELDS = frozenset({
    "title",
    "abstract",
    "author",
    "doi",
    "eprint",
    "archiveprefix",
    "url",
})


def _parse_bibtex_entries(text: str) -> list[tuple[int, int, int, str, str, list[tuple[int, int, str]]]]:
    """
    Naive BibTeX parser that finds @type{key, ...} blocks.
    Returns list of (start, body_start, end, entry_type, key, fields).
    Each field is (name_start, value_end, raw_line).
    This avoids dependency on bibtexparser.
    """
    entries = []
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.DOTALL)
    for match in entry_pattern.finditer(text):
        start = match.start()
        entry_type = match.group(1)
        key = match.group(2).strip()
        brace_start = text.index("{", start) + 1
        # Find matching closing brace
        depth = 1
        i = brace_start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        end = i  # past the closing brace
        body = text[brace_start : end - 1]  # content inside braces (excluding trailing })

        # Parse fields from body
        fields: list[tuple[int, int, str]] = []
        # Split by top-level commas (not inside braces/quotations)
        field_parts = _split_top_level_commas(body)
        for part in field_parts:
            part = part.strip()
            if not part:
                continue
            # Find field name (text before first = or {)
            eq_pos = part.find("=")
            if eq_pos == -1:
                continue
            name = part[:eq_pos].strip().lower()
            # Calculate positions relative to original text
            f_start = body.index(part) + brace_start
            f_end = f_start + len(part)
            fields.append((f_start, f_end, name))

        entries.append((start, brace_start, end, entry_type, key, fields))

    return entries


def _split_top_level_commas(text: str) -> list[str]:
    """Split on commas not inside braces or quotes."""
    parts = []
    depth = 0
    in_quotes = False
    current: list[str] = []

    for ch in text:
        if ch == '"' and not in_quotes:
            in_quotes = True
        elif ch == '"' and in_quotes:
            in_quotes = False
        elif ch == "{" and not in_quotes:
            depth += 1
        elif ch == "}" and not in_quotes:
            depth -= 1

        if ch == "," and depth == 0 and not in_quotes:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)

    if current:
        parts.append("".join(current))
    return parts


def clean_bib(text: str) -> tuple[str, list[str]]:
    """
    Remove fields not in KEEP_FIELDS from BibTeX entries.
    Returns (cleaned_text, warnings).
    """
    entries = _parse_bibtex_entries(text)
    warnings: list[str] = []

    # Build replacement list from end to start so positions stay valid
    replacements: list[tuple[int, int, str]] = []

    for start, body_start, end, entry_type, key, fields in entries:
        has_title = False
        has_abstract = False

        # We'll rebuild the body without dropped fields
        kept_field_texts: list[str] = []
        for f_start, f_end, fname in fields:
            if fname == "title":
                has_title = True
            elif fname == "abstract":
                has_abstract = True

            if fname in KEEP_FIELDS:
                kept_field_texts.append(text[f_start:f_end])

        if not has_title:
            warnings.append(f"  [{key}] Missing 'title'")
        if not has_abstract:
            warnings.append(f"  [{key}] Missing 'abstract'")

        # Reconstruct the entry: @type{key,\n  field1,\n  field2,\n}
        # Preserve original indentation from the first field
        indent = "  "
        if fields:
            # Try to detect indentation from the first field's position relative to body_start
            first_line_start = text.rfind("\n", body_start, fields[0][0]) + 1
            indent = text[first_line_start : fields[0][0]]

        new_body_parts = []
        for i, ft in enumerate(kept_field_texts):
            new_body_parts.append(f"{indent}{ft}")
        new_body = ",\n".join(new_body_parts)
        if new_body:
            new_body += ",\n"

        new_entry = f"@{entry_type}{{{key},\n{new_body}}}"
        replacements.append((start, end, new_entry))

    # Apply replacements from end to start
    replacements.sort(key=lambda x: x[0], reverse=True)
    text_chars = list(text)
    for r_start, r_end, new_text in replacements:
        text_chars[r_start:r_end] = list(new_text)

    return "".join(text_chars), warnings


def main():
    parser = argparse.ArgumentParser(
        description="Remove unnecessary BibTeX fields, keeping only those used by bib-arxiv-daily.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="BibTeX file(s) to clean")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file (only valid with a single input file). "
             "If omitted, files are modified in-place.",
    )
    args = parser.parse_args()

    if args.output and len(args.files) > 1:
        print("Error: -o/--output can only be used with a single input file.", file=sys.stderr)
        sys.exit(1)

    total_entries = 0
    total_warnings = 0

    for bib_path in args.files:
        if not bib_path.exists():
            print(f"Error: file not found: {bib_path}", file=sys.stderr)
            sys.exit(1)

        original = bib_path.read_text(encoding="utf-8")
        cleaned, warnings = clean_bib(original)

        entry_count = len(_parse_bibtex_entries(original))
        total_entries += entry_count

        if warnings:
            total_warnings += len(warnings)
            print(f"\n{bib_path}:")
            for w in warnings:
                print(w)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(cleaned, encoding="utf-8")
            print(f"\nWritten to: {args.output}")
        else:
            bib_path.write_text(cleaned, encoding="utf-8")

        kept_fields = sum(
            1 for _, _, fname in _parse_bibtex_entries(cleaned)[0][5]
        ) if entry_count > 0 else 0
        print(f"✓ {bib_path}: {entry_count} entries cleaned")

    if total_warnings > 0:
        print(f"\n⚠  {total_warnings} warning(s) — entries missing title or abstract were preserved as-is.")

    print("Done.")


if __name__ == "__main__":
    main()
