from __future__ import annotations

from datetime import datetime
import html

from models import ArxivFetchStats, LibraryLoadStats, Recommendation, RecommendationStats


_ABSTRACT_TRUNCATE = 800

def _abstract_html(text: str) -> str:
    """Return HTML with truncated abstract + expandable full text."""
    cleaned = " ".join(text.split())
    escaped = html.escape(cleaned)
    if len(cleaned) <= _ABSTRACT_TRUNCATE:
        return f"<span class='abs-text'>{escaped}</span>"
    truncated = html.escape(cleaned[:_ABSTRACT_TRUNCATE].rstrip())
    remainder = escaped[len(truncated):]
    abs_id = f"abs-{hash(cleaned[:50]) & 0xfffffff:08x}"
    return (
        f"<span class='abs-text'>{truncated}</span>"
        f"<span class='abs-ellipsis' id='{abs_id}-dots'>...</span>"
        f"<span class='abs-full' id='{abs_id}' style='display:none'>{remainder}</span>"
        f" <a href='#' class='abs-toggle' data-target='{abs_id}'"
        f" onclick=\"var e=document.getElementById('{abs_id}');"
        f"var d=document.getElementById('{abs_id}-dots');"
        f"if(e.style.display=='none'){{e.style.display='inline';d.style.display='none';"
        f"this.textContent=' less';}}else{{e.style.display='none';d.style.display='inline';"
        f"this.textContent='more';}}return false;\">more</a>"
    )


def build_report_title(recommendation_count: int, generated_at: datetime) -> str:
    return f"arXiv Daily {generated_at:%Y-%m-%d} ({recommendation_count} matches)"


def build_report_html(
    recommendations: list[Recommendation],
    library_stats: LibraryLoadStats,
    fetch_stats: ArxivFetchStats,
    recommendation_stats: RecommendationStats,
    include_pdf_links: bool,
    generated_at: datetime,
) -> str:
    match_count = len(recommendations)

    pipeline_summary = _build_pipeline_details(fetch_stats, recommendation_stats)
    library_summary = (
        f"<p class='lib-summary'>Generated {generated_at:%Y-%m-%d %H:%M UTC} &middot; "
        f"{library_stats.entries_with_abstract} library papers &middot; "
        f"{fetch_stats.fetched_candidate_count} candidates &middot; "
        f"<a href='#' onclick=\"document.getElementById('pipeline-details').style.display="
        "'block'\">details</a>"
        f"</p>"
    )

    if not recommendations:
        body = (
            "<div class='paper-card'>"
            "<p>No matching papers found. "
            f"{html.escape(_build_empty_reason(fetch_stats, recommendation_stats))}</p>"
            "</div>"
        )
        return _wrap_html(library_summary + pipeline_summary + body, match_count, generated_at)

    blocks = []
    for idx, recommendation in enumerate(recommendations, 1):
        paper = recommendation.candidate
        neighbor_items = "".join(
            f"<li>{html.escape(match.title)} <span class='sim'>({match.similarity:.3f})</span></li>"
            for match in recommendation.neighbors
        )
        links = []
        if include_pdf_links and paper.pdf_url:
            links.append(f"<a href='{html.escape(paper.pdf_url)}'>PDF</a>")
        authors = ", ".join(html.escape(author) for author in paper.authors) or "Unknown authors"
        published = paper.published.strftime("%Y-%m-%d") if paper.published else ""
        title_href = html.escape(paper.pdf_url) if paper.pdf_url else html.escape(paper.arxiv_url)
        blocks.append(
            "<div class='paper-card'>"
            "<div class='card-header'>"
            f"<span class='score'>{recommendation.score:.3f}</span>"
            f"<a class='paper-title' href='{title_href}'>{html.escape(paper.title)}</a>"
            f"<span class='date'>{published}</span>"
            "</div>"
            "<div class='card-meta'>"
            f"{authors} &middot; {' | '.join(links)}"
            "</div>"
            f"<div class='abstract'>{_abstract_html(paper.abstract)}</div>"
            "<details><summary>Closest library papers</summary>"
            f"<ul>{neighbor_items}</ul>"
            "</details>"
            "</div>"
        )

    full_content = library_summary + pipeline_summary + "".join(blocks)
    return _wrap_html(full_content, match_count, generated_at)


def _build_empty_reason(fetch_stats: ArxivFetchStats, recommendation_stats: RecommendationStats) -> str:
    if fetch_stats.query_mode == "lookback":
        if fetch_stats.fetched_candidate_count == 0:
            return f"Export API returned 0 candidates over the last {fetch_stats.lookback_days} days in the configured categories."
        if recommendation_stats.after_dedup_filter_count == 0:
            return (
                "The lookback query returned candidates, but 0 remained after dedupe / already-in-library filtering."
            )
        return "The workflow ran successfully but did not find any close arXiv papers in the requested lookback window."
    if fetch_stats.rss_new_count == 0 and fetch_stats.fallback_used and fetch_stats.fallback_candidate_count == 0:
        return (
            "RSS returned 0 new papers, and the export API fallback over the last "
            f"{fetch_stats.fallback_window_hours} hours also returned 0 candidates."
        )
    if fetch_stats.rss_new_count == 0:
        return "RSS returned 0 new papers in the configured categories."
    if recommendation_stats.after_dedup_filter_count == 0:
        return "RSS returned papers, but 0 remained after dedupe / already-in-library filtering."
    if (
        recommendation_stats.threshold_filtered_count > 0
        and recommendation_stats.final_recommendation_count == 0
    ):
        return "Candidates existed, but all of them were filtered out by the score threshold."
    return "The workflow ran successfully but did not find any new arXiv papers close to your bib corpus."


def _build_pipeline_details(fetch_stats: ArxivFetchStats, recommendation_stats: RecommendationStats) -> str:
    if fetch_stats.query_mode == "lookback":
        mode_text = f"lookback {fetch_stats.lookback_days}d"
    elif fetch_stats.fallback_used:
        mode_text = f"rss + fallback ({fetch_stats.fallback_window_hours}h)"
    else:
        mode_text = "rss"
    fallback_info = f" (fallback: {fetch_stats.fallback_candidate_count})" if fetch_stats.fallback_used else ""
    lines = [
        f"<div id='pipeline-details' class='pipeline-details' style='display:none'>",
        f"<p>Query mode: {mode_text}{fallback_info}</p>",
        f"<p>RSS new: {fetch_stats.rss_new_count} | Unique: {fetch_stats.rss_unique_count} | Fetched: {fetch_stats.fetched_candidate_count}</p>",
        f"<p>After dedupe: {recommendation_stats.after_dedup_filter_count} | Final: {recommendation_stats.final_recommendation_count}</p>",
        f"</div>",
    ]
    return "\n".join(lines)


def _build_query_summary(fetch_stats: ArxivFetchStats) -> str:
    if fetch_stats.query_mode == "lookback":
        return f"<p><strong>Query window:</strong> last {fetch_stats.lookback_days} days via export API</p>"
    return f"<p><strong>RSS new papers:</strong> {fetch_stats.rss_new_count}</p>"


def _wrap_html(content: str, match_count: int, generated_at: datetime) -> str:
    title = f"arXiv Daily {generated_at:%Y-%m-%d} ({match_count} matches)"
    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<style>"
        "* { margin: 0; padding: 0; box-sizing: border-box; }"
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
        "background: #f5f7fb; color: #16202a; padding: 16px; }"
        "h1 { font-size: 1.3rem; margin-bottom: 4px; }"
        "a { color: #0057b8; text-decoration: none; }"
        "a:hover { text-decoration: underline; }"
        ".lib-summary { font-size: 0.8rem; color: #6b7280; margin-bottom: 12px; }"
        ".paper-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; "
        "padding: 14px 16px; margin-bottom: 12px; }"
        ".card-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }"
        ".score { font-size: 0.75rem; font-weight: 600; color: #6b7280; "
        "background: #f3f4f6; border-radius: 4px; padding: 1px 6px; white-space: nowrap; flex-shrink: 0; }"
        ".paper-title { font-size: 0.95rem; font-weight: 600; color: #16202a; line-height: 1.35; }"
        ".paper-title:hover { color: #0057b8; }"
        ".date { font-size: 0.75rem; color: #9ca3af; margin-left: auto; white-space: nowrap; }"
        ".card-meta { font-size: 0.78rem; color: #6b7280; margin-bottom: 6px; display: flex; flex-wrap: wrap; gap: 6px; }"
        ".card-meta a { font-size: 0.78rem; }"
        ".abstract { font-size: 0.82rem; line-height: 1.45; color: #374151; }"
        "details { font-size: 0.78rem; margin-top: 4px; }"
        "details summary { color: #6b7280; cursor: pointer; }"
        "details ul { margin: 4px 0 0 16px; color: #6b7280; }"
        "details li { margin-bottom: 2px; }"
        ".sim { color: #9ca3af; }"
        ".pipeline-details { font-size: 0.78rem; color: #6b7280; margin-bottom: 12px; }"
        ".pipeline-details p { margin: 2px 0; }"
        ".pipeline-details summary { cursor: pointer; font-weight: 500; }"
        "</style>"
        "</head><body>"
        f"<h1>{title}</h1>"
        f"{content}"
        "</body></html>"
    )
