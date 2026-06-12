from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from index_builder import build_index_html


class IndexBuilderTest(unittest.TestCase):
    def test_empty_docs_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            html = build_index_html(docs)
            self.assertIn("No reports yet", html)
            self.assertIn("History", html)

    def test_with_one_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            report_dir = docs / "2026" / "06" / "12"
            report_dir.mkdir(parents=True)
            report_html = (
                "<html><head><title>arXiv Daily 2026-06-12 (5 matches)</title></head>"
                "<body><h1>arXiv Daily 2026-06-12 (5 matches)</h1></body></html>"
            )
            (report_dir / "index.html").write_text(report_html, encoding="utf-8")

            html = build_index_html(docs)
            self.assertIn("Latest report", html)
            self.assertIn("2026/06/12/", html)
            self.assertIn("5 matches", html)

    def test_with_multiple_reports_shows_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            for date_str in ["2026-06-10", "2026-06-11", "2026-06-12"]:
                parts = date_str.split("-")
                report_dir = docs / parts[0] / parts[1] / parts[2]
                report_dir.mkdir(parents=True)
                (report_dir / "index.html").write_text(
                    f"<html><body><h1>arXiv Daily {date_str} (3 matches)</h1></body></html>",
                    encoding="utf-8",
                )

            html = build_index_html(docs)

            # Check latest link points to the newest date
            self.assertIn("2026/06/12/", html[:html.find("History")])
            # All dates appear in history
            self.assertIn("2026-06-12", html)
            self.assertIn("2026-06-11", html)
            self.assertIn("2026-06-10", html)

    def test_rejects_invalid_path_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            # Valid report
            (docs / "2026" / "06" / "12" / "index.html").parent.mkdir(parents=True)
            (docs / "2026" / "06" / "12" / "index.html").write_text(
                "<html><body><h1>arXiv Daily 2026-06-12 (3 matches)</h1></body></html>",
                encoding="utf-8",
            )
            # Invalid path (only 2 parts deep)
            (docs / "notes" / "index.html").parent.mkdir(parents=True)
            (docs / "notes" / "index.html").write_text("irrelevant")

            html = build_index_html(docs)
            self.assertIn("2026-06-12", html)
            self.assertNotIn("notes", html)


if __name__ == "__main__":
    unittest.main()
