"""Render ASO intelligence reports to markdown, HTML, or PDF."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Template

from app.core.config import settings
from app.models.db_models import ReportFormat, ReportType

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; line-height: 1.5; }
    h1, h2 { color: #0f3d5e; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
    th { background: #f4f7fb; }
    .meta { color: #666; font-size: 0.9rem; }
    .summary { background: #f8fafc; padding: 1rem; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <p class="meta">Period: {{ period_start }} — {{ period_end }} | Generated: {{ generated_at }}</p>
  <div class="summary"><strong>Executive summary:</strong> {{ summary }}</div>

  {% if top_ideas %}
  <h2>Product ideas for you</h2>
  {% for row in top_ideas %}
  <div class="summary" style="margin-bottom: 1rem;">
    <h3>{{ row.title }}</h3>
    <p><strong>Type:</strong> {{ row.idea_type }} | <strong>Confidence:</strong> {{ row.confidence_score }}</p>
    <p><strong>Problem:</strong> {{ row.problem_statement }}</p>
    <p><strong>Solution:</strong> {{ row.proposed_solution }}</p>
    <p><strong>Audience:</strong> {{ row.target_audience }}</p>
    <p><strong>Monetization:</strong> {{ row.monetization_strategy }}</p>
  </div>
  {% endfor %}
  {% else %}
  <h2>Product ideas for you</h2>
  <p>No product ideas were available for this report. Run idea generation or lower the opportunity score threshold.</p>
  {% endif %}

  <h2>Signal counts</h2>
  <table>
    <tr><th>Source</th><th>Count</th></tr>
    {% for label, count in counts.items() %}
    <tr><td>{{ label }}</td><td>{{ count }}</td></tr>
    {% endfor %}
  </table>

  {% if top_trends %}
  <h2>Top trending apps</h2>
  <table>
    <tr><th>App</th><th>Platform</th><th>Category</th><th>Rank</th></tr>
    {% for row in top_trends %}
    <tr><td>{{ row.name }}</td><td>{{ row.platform }}</td><td>{{ row.category }}</td><td>{{ row.rank }}</td></tr>
    {% endfor %}
  </table>
  {% endif %}

  {% if top_keywords %}
  <h2>Top keyword opportunities</h2>
  <table>
    <tr><th>Term</th><th>Platform</th><th>Opportunity score</th></tr>
    {% for row in top_keywords %}
    <tr><td>{{ row.term }}</td><td>{{ row.platform }}</td><td>{{ row.opportunity_score }}</td></tr>
    {% endfor %}
  </table>
  {% endif %}

  {% if top_opportunities %}
  <h2>Top market opportunities</h2>
  <table>
    <tr><th>Title</th><th>Category</th><th>Score</th></tr>
    {% for row in top_opportunities %}
    <tr><td>{{ row.title }}</td><td>{{ row.category }}</td><td>{{ row.opportunity_score }}</td></tr>
    {% endfor %}
  </table>
  {% endif %}

  {% if review_stats %}
  <h2>Review intelligence</h2>
  <p>Negative: {{ review_stats.negative }} | Bugs mentioned: {{ review_stats.bugs }} | Feature requests: {{ review_stats.features }}</p>
  {% endif %}
</body>
</html>
""")


class ReportRenderError(Exception):
    """Raised when a report file cannot be rendered."""


def build_report_context(
    *,
    report_type: ReportType,
    period_start: datetime,
    period_end: datetime,
    generated_at: datetime,
    trends: list,
    keywords: list,
    competitors: list,
    reviews: list,
    opportunities: list,
    product_ideas: list,
) -> dict:
    counts = {
        "Trending apps": len(trends),
        "Keywords": len(keywords),
        "Competitors": len(competitors),
        "Reviews": len(reviews),
        "Opportunities": len(opportunities),
        "Product ideas": len(product_ideas),
    }
    top_opportunity = opportunities[0] if opportunities else None
    top_idea = product_ideas[0] if product_ideas else None

    negative_reviews = sum(1 for row in reviews if row.sentiment == "negative")
    bug_reviews = sum(1 for row in reviews if row.mentions_bug)
    feature_reviews = sum(1 for row in reviews if row.mentions_feature_request)

    summary_parts = [
        f"{report_type.value.title()} report with {len(product_ideas)} product idea"
        f"{'s' if len(product_ideas) != 1 else ''} ready to review."
    ]
    if counts["Trending apps"] or counts["Keywords"] or counts["Reviews"]:
        summary_parts.append(
            f"Based on {counts['Trending apps']} trending apps, {counts['Keywords']} keywords, "
            f"and {counts['Reviews']} reviews from the period."
        )
    if top_opportunity:
        summary_parts.append(
            f"Top opportunity: {top_opportunity.title} (score {top_opportunity.opportunity_score:.1f})."
            if top_opportunity.opportunity_score is not None
            else f"Top opportunity: {top_opportunity.title}."
        )
    if top_idea:
        summary_parts.append(
            f"Top idea: {top_idea.title} ({top_idea.idea_type}, confidence {top_idea.confidence_score:.1f})."
            if top_idea.confidence_score is not None
            else f"Top idea: {top_idea.title} ({top_idea.idea_type})."
        )

    title = _report_title(report_type, generated_at)
    return {
        "title": title,
        "summary": " ".join(summary_parts),
        "period_start": period_start.strftime("%Y-%m-%d %H:%M UTC"),
        "period_end": period_end.strftime("%Y-%m-%d %H:%M UTC"),
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "counts": counts,
        "top_trends": [_trend_row(row) for row in trends[:10]],
        "top_keywords": [_keyword_row(row) for row in keywords[:10]],
        "top_opportunities": [_opportunity_row(row) for row in opportunities[:10]],
        "top_ideas": [_idea_row(row) for row in product_ideas[:10]],
        "review_stats": {
            "negative": negative_reviews,
            "bugs": bug_reviews,
            "features": feature_reviews,
        },
        "competitor_count": len(competitors),
    }


def render_report_file(
    context: dict,
    report_type: ReportType,
    report_format: ReportFormat,
    generated_at: datetime,
    output_dir: str | None = None,
) -> str:
    base_dir = Path(output_dir or settings.reports_output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    stamp = generated_at.strftime("%Y-%m-%d")
    ext = _extension_for_format(report_format)
    filename = f"{report_type.value}_{stamp}.{ext}"
    path = base_dir / filename

    if report_format == ReportFormat.MARKDOWN:
        path.write_text(_render_markdown(context), encoding="utf-8")
    elif report_format == ReportFormat.HTML:
        path.write_text(_render_html(context), encoding="utf-8")
    elif report_format == ReportFormat.PDF:
        _render_pdf(context, path)
    else:
        raise ReportRenderError(f"Unsupported report format: {report_format}")

    return str(path)


def _report_title(report_type: ReportType, generated_at: datetime) -> str:
    label = "Daily" if report_type == ReportType.DAILY else "Weekly"
    return f"{label} ASO Intelligence Report — {generated_at.strftime('%Y-%m-%d')}"


def _extension_for_format(report_format: ReportFormat) -> str:
    return {
        ReportFormat.MARKDOWN: "md",
        ReportFormat.HTML: "html",
        ReportFormat.PDF: "pdf",
    }[report_format]


def _render_markdown(context: dict) -> str:
    lines = [
        f"# {context['title']}",
        "",
        f"**Period:** {context['period_start']} — {context['period_end']}",
        f"**Generated:** {context['generated_at']}",
        "",
        "## Executive summary",
        context["summary"],
        "",
    ]

    if context["top_ideas"]:
        lines.extend(["## Product ideas for you", ""])
        for row in context["top_ideas"]:
            lines.extend([
                f"### {row['title']}",
                f"- **Type:** {row['idea_type']}",
                f"- **Confidence:** {row['confidence_score']}",
                f"- **Problem:** {row['problem_statement']}",
                f"- **Solution:** {row['proposed_solution']}",
                f"- **Audience:** {row['target_audience']}",
                f"- **Monetization:** {row['monetization_strategy']}",
                "",
            ])
    else:
        lines.extend([
            "## Product ideas for you",
            "",
            "No product ideas were available for this report.",
            "",
        ])

    lines.extend(["## Signal counts"])
    for label, count in context["counts"].items():
        lines.append(f"- {label}: {count}")

    if context["top_trends"]:
        lines.extend(["", "## Top trending apps", ""])
        for row in context["top_trends"]:
            lines.append(
                f"- {row['name']} ({row['platform']}, {row['category'] or 'n/a'}, rank {row['rank']})"
            )

    if context["top_keywords"]:
        lines.extend(["", "## Top keyword opportunities", ""])
        for row in context["top_keywords"]:
            lines.append(f"- {row['term']} ({row['platform']}, score {row['opportunity_score']})")

    if context["top_opportunities"]:
        lines.extend(["", "## Top market opportunities", ""])
        for row in context["top_opportunities"]:
            lines.append(f"- {row['title']} ({row['category'] or 'n/a'}, score {row['opportunity_score']})")

    stats = context["review_stats"]
    lines.extend([
        "",
        "## Review intelligence",
        f"- Negative reviews: {stats['negative']}",
        f"- Bug mentions: {stats['bugs']}",
        f"- Feature requests: {stats['features']}",
        f"- Competitors tracked: {context['competitor_count']}",
        "",
    ])
    return "\n".join(lines)


def _render_html(context: dict) -> str:
    return HTML_TEMPLATE.render(**context)


def _render_pdf(context: dict, path: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise ReportRenderError("WeasyPrint is not installed") from exc

    try:
        HTML(string=_render_html(context)).write_pdf(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ReportRenderError(f"PDF rendering failed: {exc}") from exc


def _trend_row(row) -> dict:
    return {
        "name": row.name,
        "platform": row.platform.value if hasattr(row.platform, "value") else row.platform,
        "category": row.category,
        "rank": row.rank,
    }


def _keyword_row(row) -> dict:
    return {
        "term": row.term,
        "platform": row.platform.value if hasattr(row.platform, "value") else row.platform,
        "opportunity_score": row.opportunity_score,
    }


def _opportunity_row(row) -> dict:
    return {
        "title": row.title,
        "category": row.category,
        "opportunity_score": row.opportunity_score,
    }


def _idea_row(row) -> dict:
    return {
        "title": row.title,
        "idea_type": row.idea_type,
        "confidence_score": row.confidence_score,
        "problem_statement": row.problem_statement or "Not available",
        "proposed_solution": row.proposed_solution or "Not available",
        "target_audience": row.target_audience or "Not available",
        "monetization_strategy": row.monetization_strategy or "Not available",
    }
