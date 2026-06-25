"""
Executive PDF Report Generator - Premium Version
Treasury Intelligence System for SMEs
"""
from __future__ import annotations

import uuid
from datetime import datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.locale import normalize_locale
from app.reporting.pdf_translations import TRANSLATIONS

import os
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

def _register_arabic_fonts():
    try:
        pdfmetrics.registerFont(TTFont("Amiri", os.path.join(FONTS_DIR, "Amiri-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Amiri-Bold", os.path.join(FONTS_DIR, "Amiri-Bold.ttf")))
        pdfmetrics.registerFontFamily("Amiri", normal="Amiri", bold="Amiri-Bold")
        return True
    except Exception as e:
        print(f"Arabic font registration failed: {e}")
        return False

ARABIC_FONTS_AVAILABLE = _register_arabic_fonts()


def _shape_arabic(text: str, lang: str) -> str:
    """Shape Arabic text for correct rendering in ReportLab."""
    if lang != "ar" or not text:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text


def _get_arabic_style(base_style, font_size=None):
    """Returns a RTL Arabic-compatible paragraph style."""
    style = ParagraphStyle(
        name=base_style.name + "_ar",
        parent=base_style,
        fontName="Amiri",
        fontSize=font_size or base_style.fontSize,
        leading=(font_size or base_style.fontSize) * 1.6,
    )
    return style


# Colors matching frontend design system
NAVY = HexColor("#1e3a5f")
WHITE = HexColor("#ffffff")
LIGHT_GRAY = HexColor("#f8fafc")
SLATE = HexColor("#475569")
SUCCESS_GREEN = HexColor("#047857")
WARNING_AMBER = HexColor("#f59e0b")
DANGER_RED = HexColor("#dc2626")
BORDER = HexColor("#cbd5e0")
ACCENT_BLUE = HexColor("#3b82f6")

PAGE_W, PAGE_H = A4
MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
MARGIN_T = 22 * mm
MARGIN_B = 20 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


def _safe(obj: Any, key: str, default: Any = "") -> Any:
    if not isinstance(obj, dict):
        return default
    val = obj.get(key, default)
    return default if val is None else val


def _build_styles(is_rtl: bool = False) -> dict:
    base = getSampleStyleSheet()
    alignment = TA_RIGHT if is_rtl else TA_LEFT
    alignment_center = TA_CENTER
    font_name = "Amiri" if is_rtl and ARABIC_FONTS_AVAILABLE else "Helvetica"
    bold_font_name = "Amiri-Bold" if is_rtl and ARABIC_FONTS_AVAILABLE else "Helvetica-Bold"

    return {
        "title": ParagraphStyle(
            name="Title",
            parent=base["Title"],
            fontSize=24,
            textColor=WHITE,
            alignment=alignment,
            fontName=bold_font_name,
        ),
        "subtitle": ParagraphStyle(
            name="Subtitle",
            parent=base["Normal"],
            fontSize=12,
            textColor=HexColor("#94a3b8"),
            alignment=alignment,
            fontName=font_name,
        ),
        "cover_small": ParagraphStyle(
            name="CoverSmall",
            parent=base["Normal"],
            fontSize=10,
            textColor=ACCENT_BLUE,
            alignment=alignment,
            fontName=font_name,
        ),
        "cover_medium": ParagraphStyle(
            name="CoverMedium",
            parent=base["Normal"],
            fontSize=14,
            textColor=WHITE,
            alignment=alignment,
            fontName=font_name,
        ),
        "h1": ParagraphStyle(
            name="H1",
            parent=base["Heading1"],
            fontSize=18,
            textColor=NAVY,
            alignment=alignment,
            spaceAfter=8,
            spaceBefore=16,
            fontName=bold_font_name,
        ),
        "h2": ParagraphStyle(
            name="H2",
            parent=base["Heading2"],
            fontSize=14,
            textColor=SLATE,
            alignment=alignment,
            spaceAfter=6,
            spaceBefore=12,
            fontName=bold_font_name,
        ),
        "body": ParagraphStyle(
            name="Body",
            parent=base["BodyText"],
            fontSize=11,
            textColor=SLATE,
            alignment=alignment,
            spaceAfter=6,
            fontName=font_name,
        ),
        "body_left": ParagraphStyle(
            name="BodyLeft",
            parent=base["BodyText"],
            fontSize=11,
            textColor=SLATE,
            alignment=TA_LEFT if not is_rtl else TA_RIGHT,
            spaceAfter=6,
            fontName=font_name,
        ),
        "callout": ParagraphStyle(
            name="Callout",
            parent=base["Normal"],
            fontSize=12,
            textColor=NAVY,
            alignment=alignment,
            fontName=font_name,
        ),
        "th": ParagraphStyle(
            name="TH",
            parent=base["Normal"],
            fontSize=11,
            textColor=WHITE,
            alignment=alignment_center,
            fontName=bold_font_name,
        ),
        "td": ParagraphStyle(
            name="TD",
            parent=base["Normal"],
            fontSize=10,
            textColor=SLATE,
            alignment=alignment,
            fontName=font_name,
        ),
        "td_center": ParagraphStyle(
            name="TDCenter",
            parent=base["Normal"],
            fontSize=10,
            textColor=SLATE,
            alignment=TA_CENTER,
            fontName=font_name,
        ),
        "muted": ParagraphStyle(
            name="Muted",
            parent=base["Normal"],
            fontSize=9,
            textColor=HexColor("#94a3b8"),
            alignment=alignment,
            fontName=font_name,
        ),
    }


def _format_mad(value: Any) -> str:
    try:
        num = float(value or 0)
        return f"{num:,.2f} MAD"
    except (ValueError, TypeError):
        return str(value)


def _score_color(score: int):
    if score >= 80:
        return SUCCESS_GREEN
    elif score >= 50:
        return WARNING_AMBER
    else:
        return DANGER_RED


def _status_label(score: int, lang: str) -> str:
    t = TRANSLATIONS[lang]
    if score >= 80:
        return t["status_excellent"]
    elif score >= 50:
        return t["status_caution"]
    else:
        return t["status_critical"]


def _section_bar(title: str, styles: dict, lang: str = "fr"):
    data = [[Paragraph(escape(_shape_arabic(title, lang)), styles["h1"])]]
    table = Table(data, colWidths=[CONTENT_W])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _callout_box(content: list, bg: colors.Color = LIGHT_GRAY):
    table = Table(content, colWidths=[CONTENT_W])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ]
        )
    )
    return table


def _health_label(score: int, lang: str) -> str:
    return _status_label(score, lang)


def _resilience_label(score: int, lang: str) -> str:
    return _status_label(score, lang)


def _compute_global_grade(health: int, resilience: int, runway: int, lang: str):
    composite = (health * 0.4) + (resilience * 0.3) + (min(runway / 90 * 100, 100) * 0.3)
    if composite >= 80:
        return "A", _status_label(85, lang), composite, SUCCESS_GREEN
    elif composite >= 60:
        return "B", _status_label(70, lang), composite, WARNING_AMBER
    else:
        return "C", _status_label(40, lang), composite, DANGER_RED


def _resolve_recommended_decision(briefing: dict, decisions: list, lang: str):
    if decisions and len(decisions) > 0:
        d = decisions[0]
        return {
            "action": _safe(d, "action", ""),
            "urgency": _safe(d, "urgency", "Medium"),
            "reasoning": _safe(d, "reasoning", ""),
        }
    return {
        "action": TRANSLATIONS[lang]["recommendations_title"],
        "urgency": "Medium",
        "reasoning": "",
    }


def _build_executive_summary(
    health: int,
    resilience: int,
    runway: int,
    trend: str,
    lang: str,
):
    t = TRANSLATIONS[lang]
    if trend == "up":
        return t["executive_summary_up"].format(health=health, resilience=resilience, runway=runway)
    elif trend == "down":
        return t["executive_summary_down"].format(health=health, resilience=resilience, runway=runway)
    else:
        return t["executive_summary_stable"].format(health=health, resilience=resilience, runway=runway)


def _compute_chart_data(forecast: list, treasury_balance: float):
    if not forecast:
        return []
    data = []
    balance = treasury_balance
    for idx, f in enumerate(forecast):
        balance = float(_safe(f, "yhat", balance))
        data.append({"date": _safe(f, "ds", ""), "value": balance})
    return data


def _compute_forecast_kpis(chart_data: list, treasury_balance: float):
    if not chart_data:
        return {"trend": "stable", "min": treasury_balance, "max": treasury_balance}
    values = [d["value"] for d in chart_data]
    first = values[0]
    last = values[-1]
    trend = "stable"
    if last > first:
        trend = "up"
    elif last < first:
        trend = "down"
    return {"trend": trend, "min": min(values), "max": max(values), "first": first, "last": last}


def _generate_milestones(chart_data: list, forecast: list, lang: str):
    t = TRANSLATIONS[lang]
    milestones = []
    if len(chart_data) > 5:
        milestones.append(
            {
                "date": chart_data[min(7, len(chart_data) - 1)]["date"],
                "event": t["milestone_7d_event"],
                "impact": t["milestone_7d_impact"],
                "confidence": t["milestone_7d_confidence"],
            }
        )
    if len(chart_data) > 15:
        milestones.append(
            {
                "date": chart_data[min(15, len(chart_data) - 1)]["date"],
                "event": t["milestone_15d_event"],
                "impact": t["milestone_15d_impact"],
                "confidence": t["milestone_15d_confidence"],
            }
        )
    if len(chart_data) > 25:
        milestones.append(
            {
                "date": chart_data[min(30, len(chart_data) - 1)]["date"],
                "event": t["milestone_30d_event"],
                "impact": t["milestone_30d_impact"],
                "confidence": t["milestone_30d_confidence"],
            }
        )
    return milestones


def generate_executive_pdf_report(
    *,
    company_name: str,
    business_intelligence: dict,
    report_date: datetime | None = None,
    treasury_trend: str | None = None,
    previous_business_intelligence: dict | None = None,
    kpis: dict | None = None,
    forecast: list | None = None,
    locale: str = "fr",
) -> bytes:
    locale = normalize_locale(locale)
    lang = locale if locale in TRANSLATIONS else "fr"
    t = TRANSLATIONS[lang]
    is_rtl = lang == "ar"

    # Report metadata
    report_date = report_date or datetime.now()
    report_id = str(uuid.uuid4())[:8]
    date_short = report_date.strftime("%d/%m/%Y")
    date_long = f"{report_date.day} {t['months'][report_date.month - 1]} {report_date.year}"

    # Styles
    styles = _build_styles(is_rtl)

    # Elements container
    elements: list = []

    # Extract data from BI
    bi = business_intelligence
    health = _safe(_safe(bi, "financial_health_score", {}), "score", 50)
    resilience = _safe(_safe(bi, "treasury_resilience_score", {}), "score", 50)
    runway = _safe(_safe(bi, "cash_runway", {}), "days", 30)
    briefing = _safe(bi, "executive_briefing", {})
    risks = [r for r in (_safe(bi, "top_risks", []) or []) if isinstance(r, dict)]
    decisions = [d for d in (_safe(bi, "top_decisions", []) or []) if isinstance(d, dict)]
    treasury_balance = (_safe(kpis, "treasury_balance", 0) or 0) if kpis else 0
    net_cashflow = (_safe(kpis, "net_cashflow", 0) or 0) if kpis else 0

    # Compute derived data
    chart_data = _compute_chart_data(forecast or [], treasury_balance)
    forecast_kpis = _compute_forecast_kpis(chart_data, treasury_balance)
    trend = treasury_trend or forecast_kpis["trend"]
    grade, grade_label, composite, grade_color = _compute_global_grade(
        health, resilience, runway, lang
    )
    recommended = _resolve_recommended_decision(briefing, decisions, lang)
    milestones = _generate_milestones(chart_data, forecast or [], lang)

    # Page 1: Cover Page
    def draw_cover(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(ACCENT_BLUE)
        canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 3 * mm, fill=1, stroke=0)

        font_name = "Amiri" if is_rtl and ARABIC_FONTS_AVAILABLE else "Helvetica"
        bold_font_name = "Amiri-Bold" if is_rtl and ARABIC_FONTS_AVAILABLE else "Helvetica-Bold"

        # Grade circle
        canvas.setFillColor(WHITE)
        canvas.circle(PAGE_W - MARGIN_R - 12 * mm, PAGE_H - 45 * mm, 14 * mm, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont(bold_font_name, 24)
        canvas.drawCentredString(
            PAGE_W - MARGIN_R - 12 * mm, PAGE_H - 50 * mm, grade
        )
        canvas.setFont(font_name, 7)
        canvas.setFillColor(HexColor("#94a3b8"))
        canvas.drawCentredString(
            PAGE_W - MARGIN_R - 12 * mm, PAGE_H - 60 * mm, _shape_arabic(t["global_grade"], lang)
        )

        # Cover content
        canvas.setFillColor(WHITE)
        canvas.setFont(bold_font_name, 22)
        canvas.drawString(MARGIN_L, PAGE_H - 55 * mm, _shape_arabic(t["cover_title"], lang))
        canvas.setFont(font_name, 13)
        canvas.setFillColor(HexColor("#cbd5e1"))
        canvas.drawString(MARGIN_L, PAGE_H - 68 * mm, _shape_arabic(t["cover_subtitle"], lang))

        # Company name
        canvas.setFillColor(WHITE)
        canvas.setFont(bold_font_name, 16)
        canvas.drawString(MARGIN_L, PAGE_H - 110 * mm, company_name[:72])

        # Report metadata
        canvas.setFont(font_name, 10)
        canvas.setFillColor(HexColor("#94a3b8"))
        canvas.drawString(MARGIN_L, PAGE_H - 130 * mm, f"{_shape_arabic(t['report_date'], lang)}: {date_long}")
        canvas.drawString(MARGIN_L, PAGE_H - 142 * mm, f"{_shape_arabic(t['report_version'], lang)}: 1.0")
        canvas.drawString(MARGIN_L, PAGE_H - 154 * mm, f"{_shape_arabic(t['report_id'], lang)}: {report_id}")

        # Confidential label
        canvas.setFillColor(ACCENT_BLUE)
        canvas.setFont(bold_font_name, 8)
        canvas.drawString(MARGIN_L, PAGE_H - 175 * mm, _shape_arabic(t["confidential"], lang))

        canvas.restoreState()

    # Page 2: Executive Dashboard
    elements.append(PageBreak())
    elements.append(_section_bar(t["executive_dashboard_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(escape(_shape_arabic(t["executive_dashboard_subtitle"], lang)), styles["h2"]))
    elements.append(Spacer(1, 6 * mm))

    # KPI Interpretation helper function
    def kpi_interpretation(score, metric, lang):
        t = TRANSLATIONS[lang]
        if metric == "health":
            if score >= 80:
                return t["kpi_health_excellent"]
            elif score >= 50:
                return t["kpi_health_acceptable"]
            else:
                return t["kpi_health_fragile"]
        elif metric == "resilience":
            if score >= 80:
                return t["kpi_resilience_high"]
            elif score >= 50:
                return t["kpi_resilience_medium"]
            else:
                return t["kpi_resilience_low"]
        elif metric == "runway":
            if score >= 90:
                return t["kpi_runway_excellent"]
            elif score >= 30:
                return t["kpi_runway_sufficient"]
            else:
                return t["kpi_runway_critical"]
        return ""

    # KPI Table
    kpi_rows = [
        [
            Paragraph(escape(_shape_arabic(t["kpi_table_metric"], lang)), styles["th"]),
            Paragraph(escape(_shape_arabic(t["kpi_table_value"], lang)), styles["th"]),
            Paragraph(escape(_shape_arabic(t["kpi_table_status"], lang)), styles["th"]),
            Paragraph(escape(_shape_arabic(t["kpi_table_interpretation"], lang)), styles["th"]),
        ],
        [
            Paragraph(escape(_shape_arabic(t["kpi_health_score"], lang)), styles["td"]),
            Paragraph(f"{health}/100", styles["td_center"]),
            Paragraph(escape(_shape_arabic(_health_label(health, lang), lang)), styles["td_center"]),
            Paragraph(escape(_shape_arabic(kpi_interpretation(health, "health", lang), lang)), styles["td"]),
        ],
        [
            Paragraph(escape(_shape_arabic(t["kpi_resilience_score"], lang)), styles["td"]),
            Paragraph(f"{resilience}/100", styles["td_center"]),
            Paragraph(escape(_shape_arabic(_resilience_label(resilience, lang), lang)), styles["td_center"]),
            Paragraph(escape(_shape_arabic(kpi_interpretation(resilience, "resilience", lang), lang)), styles["td"]),
        ],
        [
            Paragraph(escape(_shape_arabic(t["kpi_cash_runway"], lang)), styles["td"]),
            Paragraph(f"{runway} {_shape_arabic(t['footer_page'].replace(t['footer_page'].split()[-1], ''), lang)}", styles["td_center"]),
            Paragraph(escape(_shape_arabic(_status_label(min(runway, 100), lang), lang)), styles["td_center"]),
            Paragraph(escape(_shape_arabic(kpi_interpretation(min(runway, 100), "runway", lang), lang)), styles["td"]),
        ],
    ]
    kpi_table = Table(kpi_rows, colWidths=[CONTENT_W * 0.22, CONTENT_W * 0.18, CONTENT_W * 0.18, CONTENT_W * 0.42])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 10 * mm))

    # Executive Summary
    elements.append(Paragraph(escape(_shape_arabic(t["executive_summary_title"], lang)), styles["h2"]))
    executive_summary = _build_executive_summary(health, resilience, runway, trend, lang)
    elements.append(Paragraph(escape(_shape_arabic(executive_summary, lang)), styles["body"]))

    # Page 3: Financial Situation Analysis
    elements.append(PageBreak())
    elements.append(_section_bar(t["financial_situation_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(escape(_shape_arabic(t["financial_situation_intro"], lang)), styles["body"]))
    elements.append(Spacer(1, 6 * mm))

    # Treasury balance and net cashflow
    treasury_row = [
        [
            Paragraph(f"<b>{escape(_shape_arabic(t['treasury_balance_label'], lang))}</b>: {_format_mad(treasury_balance)}", styles["callout"]),
            Paragraph(f"<b>{escape(_shape_arabic(t['net_cashflow_label'], lang))}</b>: {_format_mad(net_cashflow)}", styles["callout"]),
        ]
    ]
    treasury_table = Table(treasury_row, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    treasury_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ]
        )
    )
    elements.append(treasury_table)
    elements.append(Spacer(1, 10 * mm))

    # Strengths & Pressures
    elements.append(Paragraph(escape(_shape_arabic(t["strengths_pressures_title"], lang)), styles["h2"]))
    strengths = [
        t["strength_cashflow"],
        t["strength_costs"],
    ]
    pressures = [
        t["pressure_volatility"],
        t["pressure_payments"],
    ]
    sp_rows = [
        [
            Paragraph(f"<b>{escape(_shape_arabic(t['strengths_label'], lang))}</b>", styles["th"]),
            Paragraph(f"<b>{escape(_shape_arabic(t['pressures_label'], lang))}</b>", styles["th"]),
        ],
    ]
    for i in range(max(len(strengths), len(pressures))):
        s = strengths[i] if i < len(strengths) else ""
        p = pressures[i] if i < len(pressures) else ""
        sp_rows.append([Paragraph(escape(_shape_arabic(s, lang)), styles["td"]), Paragraph(escape(_shape_arabic(p, lang)), styles["td"])])
    sp_table = Table(sp_rows, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    sp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(sp_table)

    # Page 4: Strategic Decision
    elements.append(PageBreak())
    elements.append(_section_bar(t["strategic_decision_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(escape(_shape_arabic(t["strategic_decision_intro"], lang)), styles["body"]))
    elements.append(Spacer(1, 8 * mm))

    # Decision Callout
    decision_callout = [
        [Paragraph(f"<b>{escape(_shape_arabic(recommended.get('action', t['recommendations_title']), lang))}</b>", styles["callout"])],
        [Paragraph(f"{_shape_arabic(t['urgency_label'], lang)}: {escape(_shape_arabic(recommended.get('urgency', 'Medium'), lang))}", styles["muted"])],
    ]
    elements.append(_callout_box(decision_callout, LIGHT_GRAY))
    elements.append(Spacer(1, 10 * mm))

    # Decision Reasoning
    elements.append(Paragraph(escape(_shape_arabic(t["decision_reasoning_title"], lang)), styles["h2"]))
    reasoning = recommended.get("reasoning", "") or t["decision_reasoning_fallback"]
    elements.append(Paragraph(escape(_shape_arabic(reasoning, lang)), styles["body"]))
    elements.append(Spacer(1, 10 * mm))

    # Financial Justification
    elements.append(Paragraph(escape(_shape_arabic(t["financial_justification_title"], lang)), styles["h2"]))
    justification_rows = [
        [
            Paragraph(escape(_shape_arabic(t["justification_kpi"], lang)), styles["th"]),
            Paragraph(escape(_shape_arabic(t["justification_value"], lang)), styles["th"]),
            Paragraph(escape(_shape_arabic(t["justification_why"], lang)), styles["th"]),
        ],
        [
            Paragraph(escape(_shape_arabic(t["kpi_health_score"], lang)), styles["td"]),
            Paragraph(f"{health}/100", styles["td_center"]),
            Paragraph(escape(_shape_arabic(t["kpi_explanation_health"], lang)), styles["td"]),
        ],
        [
            Paragraph(escape(_shape_arabic(t["kpi_cash_runway"], lang)), styles["td"]),
            Paragraph(f"{runway} {_shape_arabic(t['footer_page'].replace(t['footer_page'].split()[-1], ''), lang)}", styles["td_center"]),
            Paragraph(escape(_shape_arabic(t["kpi_explanation_runway"], lang)), styles["td"]),
        ],
        [
            Paragraph(escape(_shape_arabic(t["treasury_balance_label"], lang)), styles["td"]),
            Paragraph(_format_mad(treasury_balance), styles["td_center"]),
            Paragraph(escape(_shape_arabic(t["kpi_explanation_balance"], lang)), styles["td"]),
        ],
    ]
    justification_table = Table(justification_rows, colWidths=[CONTENT_W * 0.3, CONTENT_W * 0.25, CONTENT_W * 0.45])
    justification_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(justification_table)

    # Page 5: Forecast & Outlook
    elements.append(PageBreak())
    elements.append(_section_bar(t["forecast_outlook_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(escape(_shape_arabic(t["forecast_intro"], lang)), styles["body"]))
    elements.append(Spacer(1, 8 * mm))

    # Outlook Narrative
    def outlook_narrative(chart_data, lang):
        t = TRANSLATIONS[lang]
        if not chart_data or len(chart_data) < 2:
            return t.get("outlook_30_days", t["forecast_intro"])
        first = chart_data[0].get("value", 0)
        last = chart_data[-1].get("value", 0)
        # Use existing translations, or just keep it simple
        return t.get("outlook_30_days", t["forecast_intro"])
    
    elements.append(Paragraph(escape(_shape_arabic(outlook_narrative(chart_data, lang), lang)), styles["body"]))
    elements.append(Spacer(1, 10 * mm))

    # Key Milestones
    if milestones:
        elements.append(Paragraph(escape(_shape_arabic(t["milestones_table_title"], lang)), styles["h2"]))
        milestone_rows = [
            [
                Paragraph(escape(_shape_arabic(t["milestone_date"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["milestone_event"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["milestone_impact"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["milestone_confidence"], lang)), styles["th"]),
            ],
        ]
        for m in milestones:
            milestone_rows.append(
                [
                    Paragraph(escape(m["date"]), styles["td"]),
                    Paragraph(escape(_shape_arabic(m["event"], lang)), styles["td"]),
                    Paragraph(escape(_shape_arabic(m["impact"], lang)), styles["td"]),
                    Paragraph(escape(_shape_arabic(m["confidence"], lang)), styles["td_center"]),
                ]
            )
        milestone_table = Table(milestone_rows, colWidths=[0.2 * CONTENT_W, 0.3 * CONTENT_W, 0.35 * CONTENT_W, 0.15 * CONTENT_W])
        milestone_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(milestone_table)
        elements.append(Spacer(1, 10 * mm))

    # Recommendations
    elements.append(Paragraph(escape(_shape_arabic(t["recommendations_title"], lang)), styles["h2"]))
    default_recs = [
        t["rec_accelerate_collections"],
        t["rec_optimize_payments"],
        t["rec_weekly_tracking"],
    ]
    for rec in default_recs:
        elements.append(Paragraph(escape(_shape_arabic(rec, lang)), styles["body_left"]))

    # Page 6: Risk Register & Opportunities
    elements.append(PageBreak())
    elements.append(_section_bar(t["risks_opportunities_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(escape(_shape_arabic(t["risks_intro"], lang)), styles["body"]))
    elements.append(Spacer(1, 10 * mm))

    # Risk Register
    if risks:
        risk_rows = [
            [
                Paragraph(escape(_shape_arabic(t["risk_table_risk"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["risk_table_severity"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["risk_table_likelihood"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["risk_table_impact"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["risk_table_mitigation"], lang)), styles["th"]),
            ],
        ]
        for risk in risks[:4]:
            risk_rows.append(
                [
                    Paragraph(escape(_shape_arabic(_safe(risk, "title", ""), lang)), styles["td"]),
                    Paragraph(escape(_shape_arabic(_safe(risk, "severity", "Medium"), lang)), styles["td_center"]),
                    Paragraph(escape(_shape_arabic(_safe(risk, "likelihood", "Medium"), lang)), styles["td_center"]),
                    Paragraph(escape(_shape_arabic(_safe(risk, "description", ""), lang)), styles["td"]),
                    Paragraph(escape(_shape_arabic(_safe(risk, "mitigation", ""), lang)), styles["td"]),
                ]
            )
        risk_table = Table(
            risk_rows,
            colWidths=[
                0.2 * CONTENT_W,
                0.12 * CONTENT_W,
                0.12 * CONTENT_W,
                0.28 * CONTENT_W,
                0.28 * CONTENT_W,
            ],
        )
        risk_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(risk_table)
        elements.append(Spacer(1, 10 * mm))

    # Opportunity Callout
    main_opp = _safe(briefing, "main_opportunity", {})
    if isinstance(main_opp, dict) and _safe(main_opp, "title", ""):
        opp_callout = [
            [Paragraph(f"<b>{escape(_shape_arabic(t['opportunity_title'], lang))}</b>: {escape(_shape_arabic(_safe(main_opp, 'title', ''), lang))}", styles["callout"])],
            [Paragraph(f"{_shape_arabic(t['opportunity_value'], lang)}: {escape(_shape_arabic(_safe(main_opp, 'potential_benefit', 'High'), lang))}", styles["muted"])],
            [Paragraph(f"{_shape_arabic(t['opportunity_action'], lang)}: {escape(_shape_arabic(_safe(main_opp, 'recommended_action', ''), lang))}", styles["muted"])],
        ]
        elements.append(_callout_box(opp_callout, LIGHT_GRAY))
    else:
        elements.append(_callout_box([[Paragraph(f"<b>{escape(_shape_arabic(t['opportunity_title'], lang))}</b>: {escape(_shape_arabic(t['default_opportunity_title'], lang))}", styles["callout"])],], LIGHT_GRAY))

    # Page 7: 90-Day Action Plan
    elements.append(PageBreak())
    elements.append(_section_bar(t["action_plan_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(escape(_shape_arabic(t["action_plan_intro"], lang)), styles["body"]))
    elements.append(Spacer(1, 10 * mm))

    # Split decisions (or use default if none)
    action_items = decisions if len(decisions) > 0 else [
        {"action": t["fallback_action_1"], "owner": "DFC", "deadline": "7 days", "priority": "High"},
        {"action": t["fallback_action_2"], "owner": "Procurement", "deadline": "30 days", "priority": "High"},
        {"action": t["fallback_action_3"], "owner": "Finance", "deadline": "30 days", "priority": "Medium"},
        {"action": t["fallback_action_4"], "owner": "CFO", "deadline": "60 days", "priority": "Medium"},
        {"action": t["fallback_action_5"], "owner": "Controller", "deadline": "90 days", "priority": "Medium"},
        {"action": t["fallback_action_6"], "owner": "HR", "deadline": "90 days", "priority": "Low"},
    ]

    plan_7d = [a for a in action_items if "7" in a.get("deadline", "") or a.get("priority") == "High"][:3]
    plan_30d = [a for a in action_items if "30" in a.get("deadline", "")][:3]
    plan_90d = [a for a in action_items if "60" in a.get("deadline", "") or "90" in a.get("deadline", "")][:3]

    def build_action_table(items, title, intro, lang, styles):
        t = TRANSLATIONS[lang]
        elements.append(Paragraph(f"<b>{escape(_shape_arabic(title, lang))}</b>", styles["h2"]))
        elements.append(Paragraph(escape(_shape_arabic(intro, lang)), styles["body"]))
        elements.append(Spacer(1, 4 * mm))

        rows = [
            [
                Paragraph(escape(_shape_arabic(t["action_table_priority"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["action_table_action"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["action_table_owner"], lang)), styles["th"]),
                Paragraph(escape(_shape_arabic(t["action_table_deadline"], lang)), styles["th"]),
            ],
        ]
        for item in items:
            priority = item.get("priority", "Medium")
            priority_label = t.get(f"priority_{priority.lower()}", priority)
            rows.append(
                [
                    Paragraph(escape(_shape_arabic(priority_label, lang)), styles["td_center"]),
                    Paragraph(escape(_shape_arabic(item.get("action", ""), lang)), styles["td"]),
                    Paragraph(escape(_shape_arabic(item.get("owner", ""), lang)), styles["td_center"]),
                    Paragraph(escape(_shape_arabic(item.get("deadline", ""), lang)), styles["td_center"]),
                ]
            )
        table = Table(rows, colWidths=[0.15 * CONTENT_W, 0.55 * CONTENT_W, 0.15 * CONTENT_W, 0.15 * CONTENT_W])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 8 * mm))

    if plan_7d:
        build_action_table(plan_7d, t["plan_7d_title"], t["plan_7d_intro"], lang, styles)
    if plan_30d:
        build_action_table(plan_30d, t["plan_30d_title"], t["plan_30d_intro"], lang, styles)
    if plan_90d:
        build_action_table(plan_90d, t["plan_90d_title"], t["plan_90d_intro"], lang, styles)

    # Page 8: Closing & Next Steps
    elements.append(PageBreak())
    elements.append(_section_bar(t["closing_title"], styles, lang))
    elements.append(Spacer(1, 6 * mm))

    # Key Decisions Recap
    elements.append(Paragraph(escape(_shape_arabic(t["key_decisions_title"], lang)), styles["h2"]))
    recap = [
        f"1. {escape(_shape_arabic(recommended.get('action', t['recap_stabilization']), lang))}",
        f"2. {escape(_shape_arabic(t['recap_7day_actions'], lang))}",
        f"3. {escape(_shape_arabic(t['recap_weekly_committee'], lang))}",
    ]
    for r in recap:
        elements.append(Paragraph(r, styles["body_left"]))
    elements.append(Spacer(1, 10 * mm))

    # What to Monitor
    elements.append(Paragraph(escape(_shape_arabic(t["what_to_monitor_title"], lang)), styles["h2"]))
    monitor = [
        f"- {_shape_arabic(t['kpi_cash_runway'], lang)}: {escape(_shape_arabic(t['monitor_runway_target'], lang))}",
        f"- {_shape_arabic(t['kpi_health_score'], lang)}: {escape(_shape_arabic(t['monitor_health_target'], lang))}",
        f"- {_shape_arabic(t['net_cashflow_label'], lang)}: {escape(_shape_arabic(t['monitor_cashflow_target'], lang))}",
    ]
    for m in monitor:
        elements.append(Paragraph(escape(m), styles["body_left"]))
    elements.append(Spacer(1, 12 * mm))

    # Disclaimer
    elements.append(_callout_box([[Paragraph(escape(_shape_arabic(t["disclaimer"], lang)), styles["muted"])],], LIGHT_GRAY))

    # Footer for all pages except cover
    def draw_page_frame(canvas, doc):
        canvas.saveState()
        # Header bar
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 13 * mm, PAGE_W, 13 * mm, fill=1, stroke=0)
        canvas.setFillColor(ACCENT_BLUE)
        canvas.rect(0, PAGE_H - 13 * mm, 3.5 * mm, 13 * mm, fill=1, stroke=0)

        font_name = "Amiri" if is_rtl and ARABIC_FONTS_AVAILABLE else "Helvetica"
        bold_font_name = "Amiri-Bold" if is_rtl and ARABIC_FONTS_AVAILABLE else "Helvetica-Bold"

        # Header text
        canvas.setFillColor(WHITE)
        canvas.setFont(bold_font_name, 8)
        canvas.drawString(MARGIN_L, PAGE_H - 9.5 * mm, _shape_arabic(t["cover_title"], lang))
        canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 9.5 * mm, f"{company_name[:30]} · {date_short}")

        # Footer
        canvas.setStrokeColor(BORDER)
        canvas.line(MARGIN_L, 13 * mm, PAGE_W - MARGIN_R, 13 * mm)
        canvas.setFont(font_name, 8)
        canvas.setFillColor(SLATE)
        footer_left = f"{_shape_arabic(t['confidential'], lang)} · {_shape_arabic(t['report_id'], lang)}: {report_id}"
        footer_right = f"{_shape_arabic(t['footer_page'], lang)} {doc.page}"
        canvas.drawString(MARGIN_L, 8 * mm, footer_left)
        canvas.drawRightString(PAGE_W - MARGIN_R, 8 * mm, footer_right)

        canvas.restoreState()

    def on_page(canvas, doc):
        if doc.page == 1:
            draw_cover(canvas, doc)
        else:
            draw_page_frame(canvas, doc)

    # Build PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 5 * mm,
        bottomMargin=MARGIN_B + 3 * mm,
        title=t["cover_title"],
        subject=t["pdf_subject"],
        author=company_name,
        creator="Treasury PME Platform",
        keywords=t["pdf_keywords"].format(company_name=company_name),
    )
    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_pdf_report(
    company_id: str,
    kpis: dict | None = None,
    forecast: list | None = None,
    recommendations: dict | None = None,
    risk_level: str | None = None,
    *,
    company_name: str | None = None,
    business_intelligence: dict | None = None,
    previous_business_intelligence: dict | None = None,
    locale: str = "fr",
) -> bytes:
    if business_intelligence:
        return generate_executive_pdf_report(
            company_name=company_name or f"Company {company_id[:8]}",
            business_intelligence=business_intelligence,
            treasury_trend=(kpis or {}).get("trend"),
            previous_business_intelligence=previous_business_intelligence,
            kpis=kpis,
            forecast=forecast,
            locale=locale,
        )
    raise ValueError("Executive report requires BI data.")
