"""
Renders the InsightReport (and supporting persona/survey data) into a
polished PDF using reportlab. This is the concrete deliverable of the
Insight Extraction Agent step described in the project spec.
"""
import os
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
)

from state import GraphState


def _p(text, style) -> Paragraph:
    """Paragraph from fully-dynamic text (no intentional markup) — always escaped."""
    return Paragraph(escape(str(text)), style)


def _p_labeled(label: str, value, style) -> Paragraph:
    """Paragraph with an intentional <b>label:</b> prefix and an escaped dynamic value."""
    return Paragraph(f"<b>{escape(str(label))}:</b> {escape(str(value))}", style)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1Custom", fontSize=20, leading=24, spaceAfter=14,
                               textColor=colors.HexColor("#1F2937")))
    styles.add(ParagraphStyle(name="H2Custom", fontSize=14, leading=18, spaceBefore=16,
                               spaceAfter=8, textColor=colors.HexColor("#374151")))
    styles.add(ParagraphStyle(name="BodyCustom", fontSize=10.5, leading=15))
    styles.add(ParagraphStyle(name="Meta", fontSize=9, textColor=colors.grey))
    return styles


def generate_pdf_report(state: GraphState, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    styles = _styles()
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             topMargin=2 * cm, bottomMargin=2 * cm,
                             leftMargin=2 * cm, rightMargin=2 * cm)
    story = []
    report = state["insight_report"]

    # Title
    story.append(Paragraph("Synthetic User Research Report", styles["H1Custom"]))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}", styles["Meta"]))
    story.append(Spacer(1, 12))

    # Context
    story.append(Paragraph("Research Context", styles["H2Custom"]))
    story.append(_p_labeled("Product", state['product_description'], styles["BodyCustom"]))
    story.append(_p_labeled("Target audience", state['target_audience'], styles["BodyCustom"]))
    story.append(_p_labeled("Research goal", state.get('research_goal', '-'), styles["BodyCustom"]))
    story.append(_p_labeled("Personas simulated", len(state['personas']), styles["BodyCustom"]))
    story.append(_p_labeled("Survey questions", len(state['survey_questions']), styles["BodyCustom"]))

    # Executive summary
    story.append(Paragraph("Executive Summary", styles["H2Custom"]))
    story.append(_p(report.executive_summary, styles["BodyCustom"]))
    story.append(_p_labeled("Overall sentiment", report.overall_sentiment.upper(), styles["BodyCustom"]))

    # Personas table
    story.append(Paragraph("Personas Surveyed", styles["H2Custom"]))
    table_data = [["Name", "Occupation", "Tech-savvy", "Key pain point"]]
    for p in state["personas"]:
        table_data.append([p.name, p.occupation, p.tech_savviness,
                            p.pain_points[0] if p.pain_points else "-"])
    t = Table(table_data, hAlign="LEFT", colWidths=[3.2 * cm, 5.5 * cm, 2.3 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(t)

    # Themes
    story.append(Paragraph("Key Themes", styles["H2Custom"]))
    for theme in report.key_themes:
        story.append(Paragraph(
            f"<b>{escape(theme.title)}</b> (prevalence: {escape(theme.prevalence)})", styles["BodyCustom"]))
        story.append(_p(theme.description, styles["BodyCustom"]))
        story.append(Paragraph(
            f"<i>Supported by: {escape(', '.join(theme.supporting_persona_ids))}</i>", styles["Meta"]))
        story.append(Spacer(1, 6))

    # Quotes
    if report.notable_quotes:
        story.append(Paragraph("Notable Quotes", styles["H2Custom"]))
        story.append(ListFlowable(
            [ListItem(_p(q, styles["BodyCustom"])) for q in report.notable_quotes],
            bulletType="bullet",
        ))

    # Weak areas / risks
    if report.weak_areas_or_risks:
        story.append(Paragraph("Weak Areas / Risks", styles["H2Custom"]))
        story.append(ListFlowable(
            [ListItem(_p(w, styles["BodyCustom"])) for w in report.weak_areas_or_risks],
            bulletType="bullet",
        ))

    # Recommendations
    story.append(Paragraph("Recommendations", styles["H2Custom"]))
    story.append(ListFlowable(
        [ListItem(_p(r, styles["BodyCustom"])) for r in report.recommendations],
        bulletType="bullet",
    ))

    doc.build(story)
    return output_path
