from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re


_DAILY_REPORT_TITLE_RE = re.compile(r"arXiv Daily (\d{4}-\d{2}-\d{2}) \((\d+) matches\)")


def _discover_reports(docs_dir: Path) -> list[dict[str, str | int]]:
    """Scan docs/YYYY/MM/DD/index.html and extract date + match count."""
    reports: list[dict[str, str | int]] = []
    if not docs_dir.is_dir():
        return reports

    date_paths = sorted(docs_dir.rglob("index.html"))
    seen: set[str] = set()
    for html_path in date_paths:
        parts = html_path.relative_to(docs_dir).parent.parts
        # Accept path patterns like 2026/06/12/index.html
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


def build_index_html(docs_dir: Path) -> str:
    """Build the index page listing all daily reports, newest first."""
    reports = _discover_reports(docs_dir)

    if not reports:
        latest_link = ""
        history_rows = "<p><em>No reports yet. Run the workflow to generate the first one.</em></p>"
    else:
        latest = reports[0]
        latest_link = (
            f"<p><strong>Latest report:</strong> "
            f"<a href=\"{latest['path']}\">{latest['date']}</a> "
            f"({latest['match_count']} matches)</p>"
        )
        rows = []
        for report in reports:
            rows.append(
                f"<li><a href=\"{report['path']}\">{report['date']}</a> "
                f"({report['match_count']} matches)</li>"
            )
        history_rows = "<ul>\n" + "\n".join(rows) + "\n</ul>"

    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'>"
        "<title>arXiv Daily Recommendations</title>"
        "<style>"
        "body { font-family: Arial, sans-serif; background: #f5f7fb; color: #16202a; margin: 0; padding: 24px; }"
        "a { color: #0057b8; text-decoration: none; }"
        "a:hover { text-decoration: underline; }"
        "h1 { margin-bottom: 4px; }"
        ".subtitle { color: #4a5568; margin-top: 0; }"
        "</style>"
        "</head><body>"
        "<h1>arXiv Daily Recommendations</h1>"
        "<p class='subtitle'>Daily paper recommendations based on your bib library.</p>"
        "<hr>"
        f"{latest_link}"
        "<h2>History</h2>"
        f"{history_rows}"
        "</body></html>"
    )
