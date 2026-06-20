from __future__ import annotations

from datetime import datetime
from html import escape, unescape
from pathlib import Path
import re
from typing import Any


_DAILY_REPORT_TITLE_RE = re.compile(r"arXiv Daily (\d{4}-\d{2}-\d{2}) \((\d+) matches\)")
_PAPERS_PER_DAY = 10
_RECENT_DAYS = 5
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _plain_text_from_html(fragment: str) -> str:
    return " ".join(unescape(_HTML_TAG_RE.sub("", fragment)).strip().split())


def _discover_reports(docs_dir: Path) -> list[dict[str, str | int]]:
    """Scan docs/YYYY/MM/DD/index.html and extract date + match count."""
    reports: list[dict[str, str | int]] = []
    if not docs_dir.is_dir():
        return reports

    date_paths = sorted(docs_dir.rglob("index.html"))
    seen: set[str] = set()
    for html_path in date_paths:
        parts = html_path.relative_to(docs_dir).parent.parts
        if len(parts) != 3:
            continue
        date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if date_str in seen:
            continue
        seen.add(date_str)

        match_count = 0
        try:
            text = html_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                m = _DAILY_REPORT_TITLE_RE.search(line)
                if m:
                    match_count = int(m.group(2))
                    break
        except Exception:
            pass

        reports.append({
            "date": date_str,
            "path": f"{parts[0]}/{parts[1]}/{parts[2]}/",
            "match_count": match_count,
        })

    reports.sort(key=lambda r: r["date"], reverse=True)
    return reports


def _parse_papers(report_path: Path) -> list[dict[str, str]]:
    """Parse all paper cards from a report file (new format)."""
    try:
        text = report_path.read_text(encoding="utf-8")
    except Exception:
        return []

    papers: list[dict[str, str]] = []
    card_pattern = re.compile(
        r"<div class='paper-card'>"
        r".*?<span class='score'>([^<]*)</span>"
        r".*?<a class='paper-title' href='([^']*)'>([^<]*)</a>"
        r".*?<span class='date'>([^<]*)</span>"
        r".*?<div class='card-meta'>(.*?)</div>"
        r".*?<div class='abstract'>(.*?)</div>",
        re.DOTALL,
    )

    for match in card_pattern.finditer(text):
        papers.append({
            "score": match.group(1).strip(),
            "url": match.group(2).strip(),
            "title": match.group(3).strip(),
            "date": match.group(4).strip(),
            "meta": " ".join(match.group(5).strip().split()),
            "abstract": _plain_text_from_html(match.group(6)),
        })

    return papers


def _build_day_section(
    report: dict[str, Any],
    papers: list[dict[str, str]],
) -> str:
    """Build the HTML for one day's paper previews."""
    items: list[str] = []
    for paper in papers[:_PAPERS_PER_DAY]:
        abstract_short = paper["abstract"][:160]
        if len(paper["abstract"]) > 160:
            abstract_short += "\u2026"
        items.append(
            '<div class="preview-item">'
            f'<span class="preview-score">{paper["score"]}</span> '
            f'<a class="preview-title" href="{escape(paper["url"])}">{escape(paper["title"])}</a>'
            f'<div class="preview-abs">{escape(abstract_short)}</div>'
            "</div>"
        )

    remainder = len(papers) - _PAPERS_PER_DAY
    if remainder > 0:
        items.append(
            f'<div class="preview-more"><a href="{report["path"]}">+ {remainder} more papers</a></div>'
        )

    return (
        '<div class="day-block">'
        f'<div class="day-header">'
        f'<h2><a href="{report["path"]}">{report["date"]}</a></h2>'
        f'<span class="day-meta">{report["match_count"]} matches</span>'
        f'<a class="day-link" href="{report["path"]}">View all &rarr;</a>'
        f"</div>"
        f'<div class="day-preview">{"".join(items)}</div>'
        f"</div>"
    )


def build_index_html(docs_dir: Path) -> str:
    """Build the index page listing all daily reports, newest first."""
    reports = _discover_reports(docs_dir)

    if not reports:
        content = (
            "<div class='empty-state'>"
            "<p><em>No reports yet. Run the workflow to generate the first one.</em></p>"
            "</div>"
        )
        history_rows = ""
    else:
        # Take the N most recent non-empty reports
        recent_reports = [r for r in reports if r["match_count"] > 0][:_RECENT_DAYS]

        # Parse papers for each recent report and build sections
        day_sections: list[str] = []
        for report in recent_reports:
            path_parts = report["path"].rstrip("/").split("/")
            report_path = docs_dir.joinpath(*path_parts, "index.html")
            papers = _parse_papers(report_path)
            if papers:
                day_sections.append(_build_day_section(report, papers))

        if day_sections:
            content = '<div class="recent-days">' + "\n".join(day_sections) + "</div>"
        else:
            # Fallback: latest report link only (maybe no new-format reports)
            latest = reports[0]
            content = (
                '<div class="empty-state">'
                f'<p>Open the <a href="{latest["path"]}">latest report</a> to see recommendations.</p>'
                "</div>"
            )

        rows = []
        for report in reports:
            rows.append(
                f'<li><a href="{report["path"]}">{report["date"]}</a>'
                f'<span class="hist-matches">({report["match_count"]} matches)</span></li>'
            )
        history_rows = "<ul>\n" + "\n".join(rows) + "\n</ul>"

    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<title>arXiv Daily Recommendations</title>"
        "<style>"
        "* { margin: 0; padding: 0; box-sizing: border-box; }"
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
        "background: #f5f7fb; color: #16202a; padding: 16px; }"
        "a { color: #0057b8; text-decoration: none; }"
        "a:hover { text-decoration: underline; }"
        "h1 { font-size: 1.3rem; margin-bottom: 2px; }"
        ".subtitle { font-size: 0.85rem; color: #6b7280; margin-bottom: 16px; }"
        ".day-block { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; "
        "padding: 14px; margin-bottom: 14px; }"
        ".day-header { display: flex; align-items: baseline; gap: 10px; "
        "margin-bottom: 8px; }"
        ".day-header h2 { font-size: 1rem; font-weight: 600; }"
        ".day-meta { font-size: 0.75rem; color: #9ca3af; }"
        ".day-link { font-size: 0.8rem; margin-left: auto; font-weight: 500; }"
        ".preview-item { padding: 5px 0; border-bottom: 1px solid #f3f4f6; }"
        ".preview-item:last-of-type { border-bottom: none; }"
        ".preview-score { font-size: 0.7rem; font-weight: 600; color: #6b7280; "
        "background: #f3f4f6; border-radius: 3px; padding: 1px 5px; margin-right: 6px; }"
        ".preview-title { font-size: 0.83rem; font-weight: 500; }"
        ".preview-abs { font-size: 0.74rem; color: #6b7280; margin: 2px 0 0 0; line-height: 1.35; }"
        ".preview-more { padding: 5px 0 0 0; font-size: 0.8rem; }"
        ".empty-state { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; "
        "padding: 24px; text-align: center; }"
        ".empty-state p { font-size: 0.85rem; color: #6b7280; }"
        "hr { border: none; border-top: 1px solid #e5e7eb; margin: 8px 0 12px 0; }"
        "h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 8px; }"
        "ul { list-style: none; padding: 0; }"
        "li { font-size: 0.85rem; padding: 4px 0; }"
        ".hist-matches { color: #9ca3af; font-size: 0.78rem; margin-left: 6px; }"
        "</style>"
        "</head><body>"
        "<h1>arXiv Daily Recommendations</h1>"
        "<p class='subtitle'>Daily paper recommendations based on your bib library.</p>"
        f"{content}"
        "<hr>"
        "<h3>History</h3>"
        f"{history_rows}"
        "</body></html>"
    )
