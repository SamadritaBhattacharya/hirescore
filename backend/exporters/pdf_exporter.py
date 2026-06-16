"""
PDF Report Exporter.

Uses Jinja2 templating + WeasyPrint to generate a professional PDF.
Runs synchronously in a thread pool to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.logging import get_logger
from models.schemas import FullReport

logger = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


class PDFExporter:
    """Generates a downloadable PDF report from FullReport data."""

    def __init__(self) -> None:
        TEMPLATE_DIR.mkdir(exist_ok=True)
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        self._ensure_template()

    async def export(self, report: FullReport) -> bytes:
        """Generate PDF bytes from report. Runs WeasyPrint in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_pdf, report)

    def _generate_pdf(self, report: FullReport) -> bytes:
        try:
            from weasyprint import HTML

            html_content = self._render_html(report)
            pdf_bytes = HTML(string=html_content).write_pdf()
            logger.info("pdf_generated", job_id=str(report.job_id))
            return pdf_bytes
        except Exception as exc:
            logger.error("pdf_generation_failed", error=str(exc))
            raise

    def _render_html(self, report: FullReport) -> str:
        template = self._env.get_template("report.html")
        verdict_colors = {
            "Strong Yes": "#16a34a",
            "Yes": "#65a30d",
            "Maybe": "#d97706",
            "No": "#dc2626",
            "Strong No": "#7f1d1d",
        }
        return template.render(
            report=report,
            verdict_color=verdict_colors.get(report.hire_verdict.value, "#374151"),
        )

    def _ensure_template(self) -> None:
        """Create the HTML template if it doesn't exist."""
        template_path = TEMPLATE_DIR / "report.html"
        if template_path.exists():
            return

        template_path.write_text(
            """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1f2937; font-size: 13px; line-height: 1.6; }
  .page { padding: 40px 48px; max-width: 800px; margin: 0 auto; }
  .header { border-bottom: 3px solid #6366f1; padding-bottom: 20px; margin-bottom: 28px; }
  .header h1 { font-size: 26px; color: #1e1b4b; font-weight: 700; }
  .header .subtitle { color: #6b7280; font-size: 13px; margin-top: 4px; }
  .candidate-name { font-size: 20px; font-weight: 600; color: #111827; margin-top: 10px; }
  .candidate-meta { color: #6b7280; font-size: 12px; margin-top: 2px; }
  .score-box { display: inline-block; padding: 12px 24px; border-radius: 10px; color: white;
               font-size: 28px; font-weight: 800; margin: 20px 0; }
  .score-label { font-size: 12px; font-weight: 400; display: block; }
  .section { margin-top: 28px; }
  .section h2 { font-size: 15px; font-weight: 700; color: #374151; border-left: 4px solid #6366f1;
                padding-left: 10px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  .summary-text { color: #374151; line-height: 1.7; }
  .flags-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .flag-card { padding: 12px; border-radius: 8px; }
  .flag-card.green { background: #f0fdf4; border: 1px solid #bbf7d0; }
  .flag-card.red { background: #fef2f2; border: 1px solid #fecaca; }
  .flag-label { font-weight: 600; font-size: 12px; margin-bottom: 4px; }
  .flag-label.green { color: #15803d; }
  .flag-label.red { color: #b91c1c; }
  .flag-evidence { color: #6b7280; font-size: 11px; }
  .skills-section { display: flex; flex-wrap: wrap; gap: 8px; }
  .skill-tag { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 500; }
  .skill-matched { background: #dbeafe; color: #1d4ed8; }
  .skill-missing { background: #fee2e2; color: #b91c1c; }
  .skill-extra { background: #f3f4f6; color: #374151; }
  .questions ol { padding-left: 20px; }
  .questions li { margin-bottom: 8px; color: #374151; }
  .analysis { color: #374151; line-height: 1.7; white-space: pre-wrap; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb;
            color: #9ca3af; font-size: 11px; text-align: center; }
  .score-row { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; }
  .culture-box { padding: 12px 20px; border-radius: 8px; background: #f5f3ff; border: 1px solid #ddd6fe; }
  .culture-score { font-size: 22px; font-weight: 700; color: #7c3aed; }
  .errors { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 12px; color: #92400e; font-size: 12px; }
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>HireScope Research Report</h1>
    <div class="subtitle">Autonomous AI Recruiting Intelligence</div>
    {% if report.candidate_name %}
    <div class="candidate-name">{{ report.candidate_name }}</div>
    <div class="candidate-meta">{{ report.candidate_headline }}{% if report.candidate_location %} · {{ report.candidate_location }}{% endif %}</div>
    {% endif %}
  </div>

  <div class="score-row">
    <div>
      <div class="score-box" style="background: {{ verdict_color }}">
        {{ report.hire_score }}<span class="score-label">Hire Score / 100 · {{ report.hire_verdict.value }}</span>
      </div>
    </div>
    {% if report.culture_fit_score %}
    <div class="culture-box">
      <div class="culture-score">{{ report.culture_fit_score }}/100</div>
      <div style="font-size:11px; color:#7c3aed;">Culture Fit Score</div>
    </div>
    {% endif %}
  </div>

  {% if report.suggested_role %}
  <div style="margin-top: 8px; font-size: 13px; color: #6b7280;">
    <strong>Role Fit:</strong> {{ report.suggested_role }}
  </div>
  {% endif %}

  {% if report.executive_summary %}
  <div class="section">
    <h2>Executive Summary</h2>
    <p class="summary-text">{{ report.executive_summary }}</p>
  </div>
  {% endif %}

  {% if report.score_breakdown %}
  <div class="section">
    <h2>Score Breakdown</h2>
    <table style="width:100%; border-collapse: collapse; font-size: 12px;">
      <tr style="background: #f9fafb;">
        <td style="padding: 8px; border: 1px solid #e5e7eb; font-weight: 600;">Component</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb; font-weight: 600;">Score</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb; font-weight: 600;">Weight</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">Skill Match</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">{{ (report.score_breakdown.skill_match_score * 100)|round|int }}%</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">40%</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">Experience Match</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">{{ (report.score_breakdown.experience_match_score * 100)|round|int }}%</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">25%</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">Project Relevance</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">{{ (report.score_breakdown.project_relevance_score * 100)|round|int }}%</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">20%</td>
      </tr>
      <tr>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">Activity Score</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">{{ (report.score_breakdown.activity_score * 100)|round|int }}%</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">15%</td>
      </tr>
    </table>
    {% if report.score_breakdown.reasoning %}
    <p style="margin-top: 10px; color: #6b7280; font-size: 12px;">{{ report.score_breakdown.reasoning }}</p>
    {% endif %}
  </div>
  {% endif %}

  {% if report.matched_skills or report.missing_skills %}
  <div class="section">
    <h2>Skills Analysis</h2>
    <div class="skills-section">
      {% for s in report.matched_skills %}<span class="skill-tag skill-matched">✓ {{ s }}</span>{% endfor %}
      {% for s in report.missing_skills %}<span class="skill-tag skill-missing">✗ {{ s }}</span>{% endfor %}
      {% for s in report.extra_skills[:5] %}<span class="skill-tag skill-extra">+ {{ s }}</span>{% endfor %}
    </div>
  </div>
  {% endif %}

  {% if report.green_flags or report.red_flags %}
  <div class="section">
    <h2>Flags</h2>
    <div class="flags-grid">
      {% for f in report.green_flags %}
      <div class="flag-card green">
        <div class="flag-label green">✅ {{ f.label }}</div>
        <div class="flag-evidence">{{ f.evidence }}</div>
      </div>
      {% endfor %}
      {% for f in report.red_flags %}
      <div class="flag-card red">
        <div class="flag-label red">⚠️ {{ f.label }}</div>
        <div class="flag-evidence">{{ f.evidence }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  {% if report.interview_questions %}
  <div class="section questions">
    <h2>Interview Questions</h2>
    <ol>{% for q in report.interview_questions %}<li>{{ q }}</li>{% endfor %}</ol>
  </div>
  {% endif %}

  {% if report.detailed_analysis %}
  <div class="section">
    <h2>Detailed Analysis</h2>
    <p class="analysis">{{ report.detailed_analysis }}</p>
  </div>
  {% endif %}

  {% if report.errors %}
  <div class="section">
    <div class="errors"><strong>Note:</strong> Some agents encountered errors: {{ report.errors | join(', ') }}</div>
  </div>
  {% endif %}

  <div class="footer">Generated by HireScope · Autonomous AI Recruiting Research Agent · {{ report.created_at.strftime('%Y-%m-%d %H:%M UTC') }}</div>
</div>
</body>
</html>"""
        )