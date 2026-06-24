"""
Rapport exécutif premium — direction / CFO / banque.

Graphiques, storytelling financier, plan 7j/30j/90j, score global A–D.
"""
from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.locale import DEFAULT_LOCALE, normalize_locale

# Palette cabinet
INK = HexColor("#1B2838")
NAVY = HexColor("#0F2B46")
ACCENT = HexColor("#C45C26")
ACCENT_LIGHT = HexColor("#FDF3EE")
SLATE = HexColor("#475569")
MUTED = HexColor("#64748B")
LINE = HexColor("#CBD5E1")
PAPER = HexColor("#F8FAFC")
WHITE = HexColor("#FFFFFF")
GREEN = HexColor("#047857")
AMBER = HexColor("#B45309")
RED = HexColor("#B91C1C")
CHART_BLUE = HexColor("#1D4ED8")
CHART_TEAL = HexColor("#0F766E")

PAGE_W, PAGE_H = A4
MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
MARGIN_T = 22 * mm
MARGIN_B = 18 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

MOIS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)

PDF_I18N = {
    "fr": {
        "months": MOIS_FR,
        "executive_view": "Vue exécutive",
        "financial_health": "SANTÉ FINANCIÈRE",
        "resilience": "RÉSILIENCE",
        "horizon": "HORIZON",
        "days_short": "j",
        "months_short": "mois",
        "trend_up": "Trésorerie en amélioration",
        "trend_stable": "Trésorerie stable",
        "trend_down": "Pression de trésorerie attendue",
        "grade_A_label": "Situation maîtrisée — pilotage préventif",
        "grade_B_label": "Situation saine — vigilance standard",
        "grade_C_label": "Situation tendue — actions correctives requises",
        "grade_D_label": "Situation fragile — arbitrage immédiat requis",
        "validate_treasury_plan": "Valider le plan de trésorerie et arbitrer les engagements des 30 prochains jours",
        "consolidate_visibility": "Consolider la visibilité cash et sécuriser la marge de manœuvre opérationnelle.",
        "stabilize_horizon": "Stabilisation de l'horizon de trésorerie et réduction de l'exposition aux chocs de flux.",
        "urgency_7d": "Sous 7 jours",
        "analysis_crosses": "L'analyse croise trois signaux : santé financière ({0}/100), résilience ({1}/100) et horizon de trésorerie ({2} jours), dans un contexte {3}.",
        "dominant_factor": "Le facteur de tension dominant est : {0}.",
        "expected_result": "Résultat attendu si la décision est exécutée : {0}",
        "consolidated_balance": "Solde de trésorerie consolidé",
        "avg_net_flow": "Flux net moyen (30 j)",
        "total_inflows": "Encaissements cumulés",
        "total_outflows": "Décaissements cumulés",
        "treasury_horizon": "Horizon de trésorerie",
        "health_resilience_index": "Indice santé / résilience",
        "overall_grade": "Notation globale",
        "days_till_tension": "Jours avant tension (estim.)",
        "grade_justification": "La notation {0} s'appuie sur un solde de {1}, un horizon de {2} jours et un flux net 30 jours de {3}. ",
        "inflow_outflow_ratio": "Le ratio encaissements/décaissements est de {0:.2f}, indicateur clé de la capacité à autofinancer l'activité.",
        "impact_financial": "Impact financier estimé : {0}.",
        "no_risk_reported": "Aucun risque majeur signalé sur la période.",
        "identified_risk": "Un risque identifié sur {0} nécessite un suivi rapproché par la direction financière.",
        "weekly_committee": "Tenir le comité de trésorerie hebdomadaire",
        "cash_suivi": "Suivi cash immédiat",
        "validate_priority_payments": "Valider la liste des paiements prioritaires",
        "secure_commitments": "Sécuriser les engagements",
        "consolidate_monthly_plan": "Consolider le plan de trésorerie mensuel",
        "30d_visibility": "Visibilité 30 jours",
        "accelerate_receivables": "Accélérer le recouvrement des créances clés",
        "improve_inflows": "Améliorer les encaissements",
        "revise_policy": "Réviser la politique de réserve de trésorerie",
        "financial_safety": "Sécurité financière",
        "renegotiate_terms": "Renégocier les conditions bancaires et le BFR",
        "optimize_structure": "Optimiser la structure financière",
        "institutionalize_committee": "Institutionnaliser le comité trésorerie trimestriel",
        "sustainable_governance": "Gouvernance durable",
        "owner_DAF": "DAF",
        "owner_Direction": "Direction",
        "owner_DG_DAF": "DG / DAF",
        "owner_DG": "DG",
        "deadline_7j": "7 jours",
        "deadline_30j": "30 jours",
        "deadline_90j": "90 jours",
        "trend_improving": "En amélioration",
        "trend_declining": "En dégradation",
        "trend_stable": "Stable",
        "severity_low": "Faible",
        "severity_medium": "Modéré",
        "severity_high": "Élevé",
        "severity_critical": "Critique",
        "urgency_15d": "Sous 15 jours",
        "urgency_30d": "Sous 30 jours",
        "risk_narrative_liquidity": "La trésorerie disponible pourrait devenir insuffisante pour couvrir les engagements immédiats.",
        "risk_narrative_cashflow": "Les entrées et sorties de cash présentent une volatilité qui fragilise la visibilité à court terme.",
        "risk_narrative_revenue": "La dépendance aux encaissements expose l'entreprise à un retard de paiement client.",
        "risk_narrative_expense": "La progression des charges réduit progressivement la marge de manœuvre financière.",
        "risk_narrative_volatility": "L'irrégularité des flux complique la planification des décaissements.",
        "risk_narrative_forecast": "La trajectoire prévisionnelle de trésorerie se dégrade sur l'horizon analysé.",
        "section_financial_story": "Fil narratif financier",
        "section_recommended_decision": "Décision recommandée",
        "subsection_arbitrage": "Arbitrage de direction (unique)",
        "urgency_label": "Urgence : ",
        "section_decision_reasoning": "Raisonnement décisionnel",
        "section_financial_justification": "Justification financière",
        "section_forecast_analysis": "Analyse des prévisions de trésorerie",
        "subsection_recommended_actions": "Actions recommandées",
        "section_risks": "Risques & vigilance — langage métier",
        "no_risks_message": "Aucun risque majeur n'a été détecté. Le pilotage peut rester en mode de surveillance standard.",
        "subsection_opportunity": "Levier d'amélioration identifié",
        "section_action_plan": "Plan d'action opérationnel",
        "plan_7d_desc": "7 jours — sécuriser le cash et exécuter la décision prioritaire",
        "plan_30d_desc": "30 jours — consolider la visibilité et corriger les écarts de flux",
        "plan_90d_desc": "90 jours — structurer la gouvernance et optimiser la structure financière",
        "treasury_balance_label": "Solde de trésorerie : ",
        "net_flow_label": " · Flux net 30j : ",
    },
    "en": {
        "months": (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ),
        "executive_view": "Executive view",
        "financial_health": "FINANCIAL HEALTH",
        "resilience": "RESILIENCE",
        "horizon": "RUNWAY",
        "days_short": "d",
        "months_short": "months",
        "trend_up": "Treasury improving",
        "trend_stable": "Treasury stable",
        "trend_down": "Expected treasury pressure",
        "grade_A_label": "Situation under control — preventive management",
        "grade_B_label": "Healthy situation — standard vigilance",
        "grade_C_label": "Tense situation — corrective actions required",
        "grade_D_label": "Fragile situation — immediate arbitration required",
        "validate_treasury_plan": "Validate the treasury plan and arbitrate commitments for the next 30 days",
        "consolidate_visibility": "Consolidate cash visibility and secure operational maneuverability.",
        "stabilize_horizon": "Stabilize the treasury horizon and reduce exposure to flow shocks.",
        "urgency_7d": "Within 7 days",
        "analysis_crosses": "The analysis combines three signals: financial health ({0}/100), resilience ({1}/100) and treasury runway ({2} days), in a {3} context.",
        "dominant_factor": "The dominant pressure factor is: {0}.",
        "expected_result": "Expected result if the decision is implemented: {0}",
        "consolidated_balance": "Consolidated treasury balance",
        "avg_net_flow": "Average net flow (30d)",
        "total_inflows": "Total inflows",
        "total_outflows": "Total outflows",
        "treasury_horizon": "Treasury runway",
        "health_resilience_index": "Health / resilience index",
        "overall_grade": "Overall rating",
        "days_till_tension": "Days before pressure (est.)",
        "grade_justification": "The {0} rating is based on a balance of {1}, a {2}-day runway and a 30-day net flow of {3}. ",
        "inflow_outflow_ratio": "The inflow/outflow ratio is {0:.2f}, a key indicator of self-financing capacity.",
        "impact_financial": "Estimated financial impact: {0}.",
        "no_risk_reported": "No major risk reported during the period.",
        "identified_risk": "An identified risk on {0} requires close monitoring by the financial department.",
        "weekly_committee": "Hold the weekly treasury committee",
        "cash_suivi": "Immediate cash monitoring",
        "validate_priority_payments": "Validate the priority payments list",
        "secure_commitments": "Secure commitments",
        "consolidate_monthly_plan": "Consolidate the monthly treasury plan",
        "30d_visibility": "30-day visibility",
        "accelerate_receivables": "Accelerate collection of key receivables",
        "improve_inflows": "Improve inflows",
        "revise_policy": "Revise the treasury reserve policy",
        "financial_safety": "Financial safety",
        "renegotiate_terms": "Renegotiate banking terms and working capital",
        "optimize_structure": "Optimize financial structure",
        "institutionalize_committee": "Institutionalize the quarterly treasury committee",
        "sustainable_governance": "Sustainable governance",
        "owner_DAF": "CFO",
        "owner_Direction": "Management",
        "owner_DG_DAF": "CEO / CFO",
        "owner_DG": "CEO",
        "deadline_7j": "7 days",
        "deadline_30j": "30 days",
        "deadline_90j": "90 days",
        "trend_improving": "Improving",
        "trend_declining": "Declining",
        "trend_stable": "Stable",
        "severity_low": "Low",
        "severity_medium": "Medium",
        "severity_high": "High",
        "severity_critical": "Critical",
        "urgency_15d": "Within 15 days",
        "urgency_30d": "Within 30 days",
        "risk_narrative_liquidity": "Available treasury could become insufficient to cover immediate commitments.",
        "risk_narrative_cashflow": "Cash inflows and outflows show volatility that weakens short-term visibility.",
        "risk_narrative_revenue": "Dependence on collections exposes the company to delayed customer payments.",
        "risk_narrative_expense": "Rising expenses gradually reduce financial maneuverability.",
        "risk_narrative_volatility": "Irregular cash flows complicate the planning of disbursements.",
        "risk_narrative_forecast": "The forecasted treasury trajectory is deteriorating over the analyzed horizon.",
        "section_financial_story": "Financial narrative thread",
        "section_recommended_decision": "Recommended decision",
        "subsection_arbitrage": "Management arbitration (single)",
        "urgency_label": "Urgency: ",
        "section_decision_reasoning": "Decision reasoning",
        "section_financial_justification": "Financial justification",
        "section_forecast_analysis": "Treasury forecast analysis",
        "subsection_recommended_actions": "Recommended actions",
        "section_risks": "Risks & vigilance — business language",
        "no_risks_message": "No major risks detected. Management can remain in standard monitoring mode.",
        "subsection_opportunity": "Improvement lever identified",
        "section_action_plan": "Operational action plan",
        "plan_7d_desc": "7 days — secure cash and execute the priority decision",
        "plan_30d_desc": "30 days — consolidate visibility and correct flow deviations",
        "plan_90d_desc": "90 days — structure governance and optimize the financial structure",
        "treasury_balance_label": "Treasury balance: ",
        "net_flow_label": " · Net 30-day flow: ",
    },
    "ar": {
        "months": (
            "يناير", "فبراير", "مارس", "أبريل", "ماي", "يونيو",
            "يوليوز", "غشت", "شتنبر", "أكتوبر", "نونبر", "دجنبر",
        ),
        "executive_view": "الرؤية التنفيذية",
        "financial_health": "الصحة المالية",
        "resilience": "المرونة",
        "horizon": "الأفق",
        "days_short": "يوم",
        "months_short": "أشهر",
        "trend_up": "تحسن وضع الخزينة",
        "trend_stable": "استقرار الخزينة",
        "trend_down": "ضغط متوقع على الخزينة",
        "grade_A_label": "موقف تحت السيطرة — إدارة وقائية",
        "grade_B_label": "وضع صحي — مراقبة عادية",
        "grade_C_label": "وضع متوتر — إجراءات تصحيحية مطلوبة",
        "grade_D_label": "وضع هش — حسم فوري مطلوب",
        "validate_treasury_plan": "التحقق من خطة الخزينة وحسم الالتزامات للـ30 يومًا القادمة",
        "consolidate_visibility": "تعزيز رؤية النقد والوضعية التشغيلية الآمنة.",
        "stabilize_horizon": "استقرار أفق الخزينة وتقليل التعرض لصدمات التدفقات.",
        "urgency_7d": "خلال 7 أيام",
        "analysis_crosses": "يتقاطع التحليل ثلاثة إشارات: الصحة المالية ({0}/100)، والمرونة ({1}/100) وأفق الخزينة ({2} يومًا)، في سياق {3}.",
        "dominant_factor": "عامل الضغط الرئيسي هو: {0}.",
        "expected_result": "النتيجة المتوقعة إذا تم تنفيذ القرار: {0}",
        "consolidated_balance": "رصيد الخزينة الموحد",
        "avg_net_flow": "صافي التدفق المتوسط (30 يومًا)",
        "total_inflows": "إجمالي الدخل",
        "total_outflows": "إجمالي المصروفات",
        "treasury_horizon": "أفق الخزينة",
        "health_resilience_index": "مؤشر الصحة / المرونة",
        "overall_grade": "التقييم العام",
        "days_till_tension": "الأيام قبل الضغط (التقدير)",
        "grade_justification": "يعتمد التقييم {0} على رصيد {1}، وأفق {2} يومًا، وصافي تدفق 30 يومًا من {3}. ",
        "inflow_outflow_ratio": "نسبة الدخل / المصروفات هو {0:.2f}، وهو مؤشر رئيسي لقدرة التمويل الذاتي.",
        "impact_financial": "التأثير المالي المقدر: {0}.",
        "no_risk_reported": "لم يتم الإبلاغ عن أي خطر كبير خلال الفترة.",
        "identified_risk": "يتطلب الخطر المحدد على {0} مراقبة وثيقة من قبل إدارة المالية.",
        "weekly_committee": "عقد لجنة الخزينة الأسبوعية",
        "cash_suivi": "مراقبة النقد الفورية",
        "validate_priority_payments": "التحقق من قائمة المدفوعات ذات الأولوية",
        "secure_commitments": "تأمين الالتزامات",
        "consolidate_monthly_plan": "تعزيز خطة الخزينة الشهرية",
        "30d_visibility": "رؤية 30 يومًا",
        "accelerate_receivables": "تسريع تحصيل المبالغ المستحقة الرئيسية",
        "improve_inflows": "تحسين الدخل",
        "revise_policy": "مراجعة سياسة احتياطي الخزينة",
        "financial_safety": "الأمن المالي",
        "renegotiate_terms": "إعادة التفاوض على الشروط المصرفية ورأس المال العامل",
        "optimize_structure": "تحسين البنية المالية",
        "institutionalize_committee": "إضفاء الطابع المؤسسي على لجنة الخزينة الفصلية",
        "sustainable_governance": "حكم مستدام",
        "owner_DAF": "مدير المالية",
        "owner_Direction": "الإدارة",
        "owner_DG_DAF": "المدير العام / مدير المالية",
        "owner_DG": "المدير العام",
        "deadline_7j": "7 أيام",
        "deadline_30j": "30 يومًا",
        "deadline_90j": "90 يومًا",
        "trend_improving": "يحسن",
        "trend_declining": "يتدهور",
        "trend_stable": "مستقر",
        "severity_low": "منخفض",
        "severity_medium": "متوسط",
        "severity_high": "عالي",
        "severity_critical": "حرج",
        "urgency_15d": "خلال 15 يومًا",
        "urgency_30d": "خلال 30 يومًا",
        "risk_narrative_liquidity": "قد تصبح الخزينة المتاحة غير كافية لتغطية الالتزامات الفورية.",
        "risk_narrative_cashflow": "تُظهر التدفقات النقدية الداخلة والخارجة تقلبًا يضعف الرؤية قصيرة الأجل.",
        "risk_narrative_revenue": "تعرض الاعتماد على التحصيلات الشركة لتأخير في مدفوعات العملاء.",
        "risk_narrative_expense": "تقلل النفقات المتزايدة تدريجيًا من مساحة المناورة المالية.",
        "risk_narrative_volatility": "تعقد التدفقات النقدية غير المنتظمة تخطيط المصروفات.",
        "risk_narrative_forecast": "تتدهور المسار المتوقع للخزينة على الأفق الذي تم تحليلته.",
        "section_financial_story": "خيوط السرد المالية",
        "section_recommended_decision": "القرار الموصى به",
        "subsection_arbitrage": "تحكيم الإدارة (فردي)",
        "urgency_label": "الأهمية العاجلة: ",
        "section_decision_reasoning": "منطق القرار",
        "section_financial_justification": "التبرير المالي",
        "section_forecast_analysis": "تحليل توقعات الخزينة",
        "subsection_recommended_actions": "الإجراءات الموصى بها",
        "section_risks": "المخاطر واليقظة — لغة الأعمال",
        "no_risks_message": "لم يتم اكتشاف أي مخاطر كبيرة. يمكن للإدارة أن تظل في وضع المراقبة القياسية.",
        "subsection_opportunity": "تم تحديد رافعة تحسين",
        "section_action_plan": "خطة العمل التشغيلية",
        "plan_7d_desc": "7 أيام — تأمين النقد وتنفيذ القرار ذي الأولوية",
        "plan_30d_desc": "30 يومًا — تعزيز الرؤية وتصحيح انحرافات التدفقات",
        "plan_90d_desc": "90 يومًا — هيكلة الحوكمة وتحسين الهيكل المالي",
        "treasury_balance_label": "رصيد الخزينة: ",
        "net_flow_label": " · تدفق صافي لمدة 30 يومًا: ",
    },
}

_PHRASES_FR: list[tuple[str, str]] = [
    ("Liquidity Risk", "Risque de liquidité"),
    ("Cashflow Risk", "Risque de flux de trésorerie"),
    ("Revenue Risk", "Risque sur les encaissements"),
    ("Expense Inflation Risk", "Risque d'inflation des charges"),
    ("Volatility Risk", "Risque de volatilité"),
    ("low", "Faible"),
    ("medium", "Modéré"),
    ("high", "Élevé"),
    ("critical", "Critique"),
    ("improving", "En amélioration"),
    ("declining", "En dégradation"),
    ("stable", "Stable"),
    ("within 30 days", "Sous 30 jours"),
    ("within 15 days", "Sous 15 jours"),
    ("within 7 days", "Sous 7 jours"),
]

_RISK_BUSINESS: dict[str, str] = {
    "liquidity risk": "La trésorerie disponible pourrait devenir insuffisante pour couvrir les engagements immédiats.",
    "cashflow risk": "Les entrées et sorties de cash présentent une volatilité qui fragilise la visibilité à court terme.",
    "revenue risk": "La dépendance aux encaissements expose l'entreprise à un retard de paiement client.",
    "expense inflation risk": "La progression des charges réduit progressivement la marge de manœuvre financière.",
    "volatility risk": "L'irrégularité des flux complique la planification des décaissements.",
    "forecast deterioration risk": "La trajectoire prévisionnelle de trésorerie se dégrade sur l'horizon analysé.",
}

_FORBIDDEN = frozenset(
    "rmse mae mape lstm prophet model algorithm ml ai prediction forecast".split()
)


def _t(locale: str, key: str, *args) -> str:
    default_locale = "fr"
    locale_dict = PDF_I18N.get(locale, PDF_I18N[default_locale])
    text = locale_dict.get(key, PDF_I18N[default_locale].get(key, key))
    if args:
        return text.format(*args)
    return text


def _safe(obj: Any, key: str, default: Any = "") -> Any:
    if not isinstance(obj, dict):
        return default
    val = obj.get(key, default)
    return default if val is None else val


def _fr(text: Any) -> str:
    # Keep this for backward compatibility, but prefer using _t() instead
    if text is None:
        return "—"
    s = str(text).strip()
    if not s:
        return "—"
    for en, fr in _PHRASES_FR:
        if en.lower() == s.lower():
            return fr
        s = re.sub(r"\b" + re.escape(en) + r"\b", fr, s, flags=re.IGNORECASE)
    return s


def _clean(text: Any) -> str:
    if text is None or text == "":
        return ""
    s = str(text).strip()
    if not s:
        return ""
    for word in _FORBIDDEN:
        s = re.sub(r"\b" + word + r"\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return escape(s)


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    clean = _clean(_fr(text))
    return Paragraph(clean if clean else "—", style)


def _health_label(score: int | float | None) -> str:
    try:
        s = int(score or 0)
    except Exception:
        s = 0
    if s >= 80:
        return "Excellente"
    if s >= 60:
        return "Bonne"
    if s >= 40:
        return "Modérée"
    return "Fragile"


def _resilience_label(score: int | float | None) -> str:
    try:
        s = int(score or 0)
    except Exception:
        s = 0
    if s >= 80:
        return "Forte"
    if s >= 60:
        return "Correcte"
    if s >= 40:
        return "Limitée"
    return "Fragilisée"


def _score_color(score: int) -> HexColor:
    if score >= 70:
        return GREEN
    if score >= 50:
        return AMBER
    return RED


def _compute_global_grade(
    health_score: int,
    resilience_score: int,
    runway_days: int,
    locale: str = "fr"
) -> tuple[str, str, int, HexColor]:
    """Score composite → notation A/B/C/D (style rating cabinet)."""
    runway_norm = min(100, int(runway_days / 3.65))
    composite = int(0.40 * health_score + 0.35 * resilience_score + 0.25 * runway_norm)
    if composite >= 75:
        return "A", _t(locale, "grade_A_label"), composite, GREEN
    if composite >= 60:
        return "B", _t(locale, "grade_B_label"), composite, HexColor("#0F766E")
    if composite >= 45:
        return "C", _t(locale, "grade_C_label"), composite, AMBER
    return "D", _t(locale, "grade_D_label"), composite, RED


def _resolve_recommended_decision(briefing: dict, decisions: list[dict], locale: str = "fr") -> dict:
    """Une seule décision recommandée pour la direction."""
    rec = _safe(briefing, "recommended_decision", {})
    if isinstance(rec, dict) and _safe(rec, "action", ""):
        return {
            "action": _safe(rec, "action", ""),
            "rationale": _safe(rec, "rationale", "") or _safe(rec, "why", ""),
            "expected_outcome": _safe(rec, "expected_outcome", "") or _safe(rec, "expected_benefit", ""),
            "urgency": _safe(rec, "urgency", ""),
        }
    if decisions:
        d = decisions[0]
        return {
            "action": _safe(d, "action", "") or _safe(d, "recommended_action", "") or _safe(d, "title", ""),
            "rationale": _safe(d, "business_justification", "") or _safe(d, "reasoning", ""),
            "expected_outcome": _safe(d, "expected_benefit", ""),
            "urgency": _safe(d, "urgency", ""),
        }
    return {
        "action": _t(locale, "validate_treasury_plan"),
        "rationale": _t(locale, "consolidate_visibility"),
        "expected_outcome": _t(locale, "stabilize_horizon"),
        "urgency": _t(locale, "urgency_7d"),
    }


def _build_decision_reasoning(
    decision: dict,
    risks: list[dict],
    health_score: int,
    resilience_score: int,
    runway_days: int,
    trend: str | None,
    locale: str = "fr"
) -> str:
    """Raisonnement décisionnel en langage direction."""
    parts: list[str] = []
    rationale = _clean(decision.get("rationale", ""))
    if rationale and rationale != "—":
        parts.append(rationale)

    # Get trend translation
    if trend:
        trend_lower = trend.lower()
        if "improving" in trend_lower or "en amélioration" in trend_lower:
            trend_trans = _t(locale, "trend_improving")
        elif "declining" in trend_lower or "en dégradation" in trend_lower:
            trend_trans = _t(locale, "trend_declining")
        else:
            trend_trans = _t(locale, "trend_stable")
    else:
        trend_trans = _t(locale, "trend_stable")

    parts.append(_t(locale, "analysis_crosses", health_score, resilience_score, runway_days, trend_trans))
    if risks:
        main = _safe(risks[0], "title", "")
        if main != "—":
            parts.append(_t(locale, "dominant_factor", main.lower()))
    outcome = _clean(decision.get("expected_outcome", ""))
    if outcome and outcome != "—":
        parts.append(_t(locale, "expected_result", outcome))
    return " ".join(parts)


def _build_financial_justification(
    kpis: dict | None,
    health_score: int,
    resilience_score: int,
    runway_days: int,
    grade: str,
    locale: str = "fr"
) -> tuple[str, list[list[str]]]:
    """Justification financière chiffrée."""
    k = kpis or {}
    balance = k.get("treasury_balance")
    net_30 = k.get("net_cashflow") or k.get("avg_daily_cashflow")
    inflows = k.get("total_inflows")
    outflows = k.get("total_outflows")
    days_zero = k.get("days_until_zero")

    rows = [
        [_t(locale, "consolidated_balance"), _format_mad(balance)],
        [_t(locale, "avg_net_flow"), _format_mad(net_30)],
        [_t(locale, "total_inflows"), _format_mad(inflows)],
        [_t(locale, "total_outflows"), _format_mad(outflows)],
        [_t(locale, "treasury_horizon"), f"{runway_days} {_t(locale, 'days_short')} ({max(1, runway_days // 30)} {_t(locale, 'months_short')})"],
        [_t(locale, "health_resilience_index"), f"{health_score} / {resilience_score}"],
        [_t(locale, "overall_grade"), grade],
    ]
    if days_zero is not None:
        rows.append([_t(locale, "days_till_tension"), f"{days_zero} {_t(locale, 'days_short')}"])

    narrative = _t(locale, "grade_justification", grade, _format_mad(balance), runway_days, _format_mad(net_30))
    if inflows and outflows:
        try:
            ratio = float(inflows) / max(float(outflows), 1)
            narrative += _t(locale, "inflow_outflow_ratio", ratio)
        except (TypeError, ValueError):
            pass
    return narrative, rows


def _is_plan_30d(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("30 jour", "30j", "mois", "month", "mensuel"))


def _is_plan_90d(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("90 jour", "90j", "trimestre", "quarter", "3 mois", "structurer", "politique"))


def _format_mad(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{n:,.0f}".replace(",", " ") + " MAD"


def _risk_business_narrative(risk: dict, locale: str = "fr") -> str:
    title = str(_safe(risk, "title", "")).strip()
    desc = _clean(_safe(risk, "description", ""))
    key = title.lower()
    
    # Map risk types to keys in PDF_I18N
    risk_map = {
        "liquidity risk": "risk_narrative_liquidity",
        "cashflow risk": "risk_narrative_cashflow",
        "cash flow risk": "risk_narrative_cashflow",
        "revenue risk": "risk_narrative_revenue",
        "expense inflation risk": "risk_narrative_expense",
        "volatility risk": "risk_narrative_volatility",
        "forecast deterioration risk": "risk_narrative_forecast",
    }
    
    # Find matching risk narrative
    base = None
    for pattern, key_name in risk_map.items():
        if pattern in key:
            base = _t(locale, key_name)
            break
            
    # If no match, use generic or existing desc
    if not base:
        if desc and desc != "—":
            return desc
        if title:
            return _t(locale, "identified_risk", title.lower())
        return _t(locale, "no_risk_reported")
        
    # Add impact and desc if available
    impact = _safe(risk, "estimated_financial_impact", "")
    if impact and str(impact) != "—":
        base += " " + _t(locale, "impact_financial", impact)
        
    if desc and desc != "—":
        return f"{base} {desc}"
        
    return base


def _is_urgent_7d(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("7 jour", "7j", "semaine", "week", "immédiat", "urgent", "critical", "high", "élevé", "critique"))


def _split_action_plans(
    briefing: dict,
    decisions: list[dict],
    locale: str = "fr"
) -> tuple[list[dict], list[dict], list[dict]]:
    """Répartit actions en plan 7 / 30 / 90 jours."""
    plan_7: list[dict] = []
    plan_30: list[dict] = []
    plan_90: list[dict] = []
    seen: set[str] = set()

    def add(action: str, why: str, owner: str, deadline: str, force_bucket: str | None = None):
        action = str(action or "").strip()
        if not action or action in seen:
            return
        seen.add(action)
        item = {"action": action, "why": why, "owner": owner, "deadline": deadline or "—"}
        ctx = f"{deadline} {action}".lower()
        if force_bucket == "7" or _is_urgent_7d(ctx):
            plan_7.append(item)
        elif force_bucket == "90" or _is_plan_90d(ctx):
            plan_90.append(item)
        elif force_bucket == "30" or _is_plan_30d(ctx):
            plan_30.append(item)
        else:
            plan_30.append(item)

    for act in _safe(briefing, "immediate_actions", []) or []:
        if isinstance(act, dict):
            add(
                _safe(act, "action", ""),
                _safe(act, "why", "") or _safe(act, "rationale", ""),
                _safe(act, "owner", _t(locale, "owner_DAF")),
                _safe(act, "deadline", "") or _safe(act, "urgency", ""),
            )
        elif act:
            add(str(act), "", _t(locale, "owner_DAF"), "")

    for d in decisions[1:]:
        add(
            _safe(d, "action", "") or _safe(d, "recommended_action", ""),
            _safe(d, "business_justification", "") or _safe(d, "expected_benefit", ""),
            _safe(d, "owner", _t(locale, "owner_Direction")),
            _safe(d, "urgency", "") or _safe(d, "time_horizon", ""),
        )

    if not plan_7:
        plan_7 = [
            {"action": _t(locale, "weekly_committee"), "why": _t(locale, "cash_suivi"), "owner": _t(locale, "owner_DAF"), "deadline": _t(locale, "deadline_7j")},
            {"action": _t(locale, "validate_priority_payments"), "why": _t(locale, "secure_commitments"), "owner": _t(locale, "owner_DAF"), "deadline": _t(locale, "deadline_7j")},
        ]
    if not plan_30:
        plan_30 = [
            {"action": _t(locale, "consolidate_monthly_plan"), "why": _t(locale, "30d_visibility"), "owner": _t(locale, "owner_DAF"), "deadline": _t(locale, "deadline_30j")},
            {"action": _t(locale, "accelerate_receivables"), "why": _t(locale, "improve_inflows"), "owner": _t(locale, "owner_Direction"), "deadline": _t(locale, "deadline_30j")},
        ]
    if not plan_90:
        plan_90 = [
            {"action": _t(locale, "revise_policy"), "why": _t(locale, "financial_safety"), "owner": _t(locale, "owner_DG_DAF"), "deadline": _t(locale, "deadline_90j")},
            {"action": _t(locale, "renegotiate_terms"), "why": _t(locale, "optimize_structure"), "owner": _t(locale, "owner_DAF"), "deadline": _t(locale, "deadline_90j")},
            {"action": _t(locale, "institutionalize_committee"), "why": _t(locale, "sustainable_governance"), "owner": _t(locale, "owner_DG"), "deadline": _t(locale, "deadline_90j")},
        ]
    return plan_7[:4], plan_30[:5], plan_90[:4]


def _build_styles() -> dict[str, ParagraphStyle]:
    ss = getSampleStyleSheet()
    return {
        "section": ParagraphStyle(
            "section", parent=ss["Heading2"],
            fontSize=12, leading=14, textColor=NAVY, fontName="Helvetica-Bold",
            spaceBefore=5, spaceAfter=3,
        ),
        "subsection": ParagraphStyle(
            "subsection", parent=ss["Heading3"],
            fontSize=10, leading=12, textColor=INK, fontName="Helvetica-Bold",
            spaceBefore=3, spaceAfter=2,
        ),
        "story": ParagraphStyle(
            "story", parent=ss["Normal"],
            fontSize=10, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", parent=ss["Normal"],
            fontSize=9, leading=12.5, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=2,
        ),
        "body_left": ParagraphStyle(
            "body_left", parent=ss["Normal"],
            fontSize=9, leading=12, textColor=INK, alignment=TA_LEFT, spaceAfter=2,
        ),
        "muted": ParagraphStyle(
            "muted", parent=ss["Normal"],
            fontSize=8, leading=10.5, textColor=MUTED, spaceAfter=2,
        ),
        "callout": ParagraphStyle(
            "callout", parent=ss["Normal"],
            fontSize=9.5, leading=13, textColor=INK, alignment=TA_JUSTIFY,
        ),
        "hero_value": ParagraphStyle(
            "hero_value", parent=ss["Normal"],
            fontSize=34, leading=36, textColor=NAVY, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=0,
        ),
        "hero_label": ParagraphStyle(
            "hero_label", parent=ss["Normal"],
            fontSize=8, leading=10, textColor=MUTED, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=2,
        ),
        "hero_status": ParagraphStyle(
            "hero_status", parent=ss["Normal"],
            fontSize=9, leading=11, textColor=SLATE, alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=ss["Normal"],
            fontSize=9, leading=12, textColor=INK, leftIndent=8, spaceAfter=2,
        ),
        "th": ParagraphStyle(
            "th", parent=ss["Normal"],
            fontSize=8, leading=10, textColor=WHITE, fontName="Helvetica-Bold",
        ),
        "td": ParagraphStyle(
            "td", parent=ss["Normal"],
            fontSize=8.5, leading=11, textColor=INK,
        ),
        "td_right": ParagraphStyle(
            "td_right", parent=ss["Normal"],
            fontSize=8.5, leading=11, textColor=INK, alignment=2,
        ),
        "chart_caption": ParagraphStyle(
            "chart_caption", parent=ss["Normal"],
            fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=3,
        ),
        "grade_letter": ParagraphStyle(
            "grade_letter", parent=ss["Normal"],
            fontSize=48, leading=50, fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "grade_label": ParagraphStyle(
            "grade_label", parent=ss["Normal"],
            fontSize=9, leading=11, textColor=SLATE, alignment=TA_CENTER, spaceAfter=0,
        ),
    }


def _section_bar(title: str, styles: dict[str, ParagraphStyle]) -> Table:
    bar_w = 3 * mm
    t = Table([[None, _p(title.upper(), styles["section"])]], colWidths=[bar_w, CONTENT_W - bar_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _callout_box(paragraphs: list, bg: HexColor = ACCENT_LIGHT) -> Table:
    inner = Table([[p] for p in paragraphs], colWidths=[CONTENT_W - 16])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return inner


def _grade_badge(
    grade: str,
    label: str,
    composite: int,
    color: HexColor,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Badge notation globale A/B/C/D."""
    inner = Table(
        [[Paragraph(f'<font color="{color.hexval()}">{escape(grade)}</font>', styles["grade_letter"])]],
        colWidths=[28 * mm],
    )
    inner.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    right = Table(
        [
            [_p("NOTATION GLOBALE", styles["hero_label"])],
            [_p(label, styles["grade_label"])],
            [_p(f"Score composite : {composite}/100", styles["muted"])],
        ],
        colWidths=[CONTENT_W - 34 * mm],
    )
    row = Table([[inner, right]], colWidths=[32 * mm, CONTENT_W - 32 * mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("BOX", (0, 0), (-1, -1), 1, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return row


def _financial_table(rows: list[list[str]], styles: dict) -> Table:
    data = [[_p("Indicateur", styles["th"]), _p("Valeur", styles["th"])]]
    for label, val in rows:
        data.append([_p(label, styles["td"]), _p(val, styles["td_right"])])
    t = Table(data, colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.25, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PAPER]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _hero_kpi(label: str, value: str, status: str, accent: HexColor, styles: dict) -> Table:
    w = (CONTENT_W - 6) / 3
    gauge = _score_gauge_drawing(
        int(re.sub(r"[^\d]", "", value) or "0") if value.replace("j", "").isdigit() else 50,
        w - 8,
        14,
        accent,
    )
    data = [
        [_p(label, styles["hero_label"])],
        [Paragraph(f'<font color="{accent.hexval()}">{escape(value)}</font>', styles["hero_value"])],
        [_p(status, styles["hero_status"])],
        [gauge],
    ]
    t = Table(data, colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("LINEABOVE", (0, 0), (-1, 0), 3, accent),
        ("BOX", (0, 0), (-1, -1), 0.75, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def _score_gauge_drawing(score: int, width: float, height: float, color: HexColor) -> Drawing:
    pct = max(0.0, min(1.0, score / 100.0))
    d = Drawing(width, height + 4)
    d.add(Rect(0, 2, width, height, fillColor=PAPER, strokeColor=LINE, strokeWidth=0.5))
    d.add(Rect(0, 2, width * pct, height, fillColor=color, strokeColor=None))
    return d


def _cashflow_bar_chart(kpis: dict | None, width: float = CONTENT_W, height: float = 95) -> Drawing | None:
    if not kpis:
        return None
    inflow = float(kpis.get("total_inflows") or 0)
    outflow = float(kpis.get("total_outflows") or 0)
    if inflow <= 0 and outflow <= 0:
        return None
    d = Drawing(width, height)
    d.add(String(0, height - 12, "Structure des flux (période analysée)", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    bc = HorizontalBarChart()
    bc.x = 95
    bc.y = 12
    bc.height = 55
    bc.width = width - 110
    bc.data = [[inflow / 1000, outflow / 1000]]
    bc.categoryAxis.categoryNames = ["Encaissements", "Décaissements"]
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.valueMin = 0
    bc.valueAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = 7
    bc.bars[0].fillColor = CHART_TEAL
    bc.bars[0].strokeColor = None
    bc.bars[1].fillColor = ACCENT
    bc.bars[1].strokeColor = None
    d.add(bc)
    d.add(String(width - 80, 12, "k MAD", fontName="Helvetica", fontSize=7, fillColor=MUTED))
    return d


def _compute_chart_data(forecast: list | None, treasury_balance: float | None) -> list[dict]:
    """
    Computes chart data exactly like frontend ForecastChart!
    Returns list of {"ds": date_str, "projectedBalance": float}
    """
    if not forecast or treasury_balance is None:
        return []
    
    # Sort forecast by date (like frontend) - convert to date for proper sorting
    sorted_forecast = sorted(
        [f for f in forecast if f.get("ds") or f.get("date")],
        key=lambda x: (x.get("ds") or x.get("date"))
    )
    
    chart_data = []
    
    for point in sorted_forecast:
        ds = point.get("ds") or point.get("date")
        try:
            # yhat from Prophet/LSTM is already the absolute treasury balance at that date, not a delta
            projected_balance = float(point.get("yhat") or point.get("prediction") or 0)
            chart_data.append({
                "ds": ds,
                "projectedBalance": projected_balance
            })
        except (TypeError, ValueError):
            continue
    
    return chart_data


def _compute_forecast_kpis(chart_data: list[dict], treasury_balance: float | None) -> dict:
    """
    Computes forecast KPIs exactly like frontend ForecastChart!
    Returns: {currentBalance, projectedBalance, variation, variationPercent, horizon, trend}
    """
    if not chart_data or treasury_balance is None:
        return {
            "currentBalance": treasury_balance,
            "projectedBalance": treasury_balance,
            "variation": 0,
            "variationPercent": 0,
            "horizon": 0,
            "trend": "stable"
        }
    
    projected_balance = chart_data[-1]["projectedBalance"]
    variation = projected_balance - float(treasury_balance)
    variation_percent = (variation / float(treasury_balance)) * 100 if float(treasury_balance) != 0 else 0
    horizon = len(chart_data)
    
    first_val = chart_data[0]["projectedBalance"]
    last_val = projected_balance
    if last_val > first_val:
        trend = "up"
    elif last_val < first_val:
        trend = "down"
    else:
        trend = "stable"
    
    return {
        "currentBalance": treasury_balance,
        "projectedBalance": projected_balance,
        "variation": variation,
        "variationPercent": variation_percent,
        "horizon": horizon,
        "trend": trend
    }


def _generate_forecast_narrative(
    forecast_kpis: dict,
    kpis: dict | None,
    risks: list[dict],
    decisions: list[dict],
    briefing: dict,
) -> tuple[str, list[str]]:
    """
    Génère une analyse narrative intelligente des prévisions de trésorerie.
    Retourne (texte_principal, liste_recommandations)
    """
    current_balance = _format_mad(forecast_kpis["currentBalance"])
    projected_balance = _format_mad(forecast_kpis["projectedBalance"])
    variation_percent = forecast_kpis["variationPercent"]
    variation_amount = _format_mad(forecast_kpis["variation"])
    horizon_days = forecast_kpis["horizon"]
    
    # Générer le texte principal selon la situation
    if variation_percent > 3:
        main_text = (
            f"La trésorerie projetée progresse sur l’horizon des {horizon_days} prochains jours. "
            f"Le solde estimé passerait de {current_balance} à {projected_balance}, soit une amélioration de {variation_percent:.1f} %. "
            f"Cette évolution traduit une dynamique favorable des flux financiers et renforce la capacité de l’entreprise à financer ses opérations et ses projets de développement."
        )
    elif -3 <= variation_percent <= 3:
        main_text = (
            "La trésorerie demeure globalement stable sur l’horizon de projection. "
            f"Les flux entrants et sortants restent relativement équilibrés et ne présentent pas de risque immédiat pour la liquidité de l’entreprise. "
            f"Une surveillance régulière est néanmoins recommandée afin de préserver cet équilibre."
        )
    elif -10 < variation_percent < -3:
        main_text = (
            f"Les projections indiquent une baisse progressive de la trésorerie sur les {horizon_days} prochains jours. "
            f"Le solde devrait passer de {current_balance} à {projected_balance}, soit une diminution estimée de {variation_amount} ({variation_percent:.1f} %). "
            f"Cette évolution nécessite une vigilance particulière afin de préserver les équilibres financiers à court terme."
        )
    else:
        main_text = (
            f"Les prévisions signalent une détérioration significative de la trésorerie. "
            f"Le niveau de liquidité devrait reculer de {variation_percent:.1f} % sur l’horizon étudié. "
            f"Sans action corrective, cette tendance pourrait réduire la capacité de l’entreprise à absorber les dépenses imprévues et à financer son activité. "
            f"Une action rapide sur les encaissements et les dépenses discrétionnaires est recommandée."
        )
    
    # Générer les recommandations
    recommendations = []
    
    # Ajouter la décision recommandée du briefing
    recommended_decision = _safe(briefing, "recommended_decision", {})
    if isinstance(recommended_decision, dict) and _safe(recommended_decision, "action", ""):
        action_text = _clean(_safe(recommended_decision, "action", ""))
        if action_text and action_text != "—":
            recommendations.append(action_text)
    
    # Ajouter des recommandations depuis les décisions
    for decision in decisions:
        action_text = _safe(decision, "action", "") or _safe(decision, "recommended_action", "") or _safe(decision, "title", "")
        cleaned_action = _clean(action_text)
        if cleaned_action and cleaned_action != "—" and cleaned_action not in recommendations:
            recommendations.append(cleaned_action)
            if len(recommendations) >= 4:
                break
    
    # Ajouter des recommandations depuis les risques
    for risk in risks:
        risk_title = _fr(_safe(risk, "title", ""))
        if risk_title and risk_title != "—":
            # Transformer le risque en recommandation
            if "encaissement" in risk_title.lower() or "créance" in risk_title.lower():
                recommendations.append("Accélérer le recouvrement des créances en attente.")
            elif "dépense" in risk_title.lower() or "sortant" in risk_title.lower():
                recommendations.append("Réduire les dépenses discrétionnaires non prioritaires.")
            elif "fournisseur" in risk_title.lower() or "échéance" in risk_title.lower():
                recommendations.append("Sécuriser les principales échéances fournisseurs.")
            elif "liquidité" in risk_title.lower():
                recommendations.append("Renforcer le suivi des encaissements confirmés.")
            if len(recommendations) >= 4:
                break
    
    # Si pas assez de recommandations, ajouter des défauts
    default_recommendations = [
        "Accélérer le recouvrement des créances en attente.",
        "Renforcer le suivi des encaissements confirmés.",
        "Réduire les dépenses discrétionnaires non prioritaires.",
        "Sécuriser les principales échéances fournisseurs.",
    ]
    for rec in default_recommendations:
        if len(recommendations) >= 4:
            break
        if rec not in recommendations:
            recommendations.append(rec)
    
    # Prendre 2-4 recommandations
    return main_text, recommendations[:4]


def _treasury_outlook_chart(
    chart_data: list[dict],
    treasury_balance: float | None,
    width: float = CONTENT_W,
    height: float = 130,
) -> Drawing | None:
    if len(chart_data) < 1 or treasury_balance is None:
        return None
    
    # Prepare data points for chart exactly like frontend (only chart_data points)
    points = [(i, float(p["projectedBalance"])) for i, p in enumerate(chart_data)]
    
    d = Drawing(width, height)
    d.add(String(0, height - 12, "Trajectoire prévisionnelle de trésorerie", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    plot = LinePlot()
    plot.x = 35
    plot.y = 18
    plot.height = height - 38
    plot.width = width - 50
    plot.data = [points]
    plot.lines[0].strokeColor = CHART_BLUE
    plot.lines[0].strokeWidth = 2
    plot.lines[0].symbol = makeMarker("Circle")
    plot.lines[0].symbol.size = 3
    plot.lines[0].symbol.fillColor = CHART_BLUE
    plot.xValueAxis.valueMin = 0
    plot.xValueAxis.valueMax = len(points) - 1
    plot.xValueAxis.labels.fontSize = 7
    plot.yValueAxis.labels.fontSize = 7
    plot.yValueAxis.labelTextFormat = lambda v: f"{v/1000:.0f}k"
    d.add(plot)
    return d


def _financial_story(
    company: str,
    kpis: dict | None,
    briefing: dict,
    health_lbl: str,
    trend: str | None,
) -> str:
    balance = _format_mad((kpis or {}).get("treasury_balance"))
    trend_fr = _fr(trend).lower() if trend else "stable"
    situation = _clean(_safe(briefing, "financial_situation", ""))
    summary = _clean(_safe(briefing, "executive_summary", ""))

    opener = (
        f"<b>{escape(company)}</b> affiche une trésorerie {health_lbl.lower()} "
        f"avec un solde consolidé de {balance}. "
        f"La dynamique récente est {trend_fr}."
    )
    if situation and situation != "—":
        return f"{opener} {situation}"
    if summary and summary != "—":
        return f"{opener} {summary}"
    return opener


def _forecast_kpi_block(
    forecast_kpis: dict,
    trend_label: str,
    trend_color: HexColor,
    styles: dict
) -> Table:
    """Builds forecast KPI block exactly like frontend ForecastChart!"""
    
    # Format values
    current_balance = _format_mad(forecast_kpis["currentBalance"])
    projected_balance = _format_mad(forecast_kpis["projectedBalance"])
    variation_percent = f"{'+'.join(['']) if forecast_kpis['variationPercent'] >= 0 else ''}{forecast_kpis['variationPercent']:.1f}%"
    variation_percent = f"{'+'.join('') if forecast_kpis['variationPercent'] >=0 else ''}{forecast_kpis['variationPercent']:.1f}%"
    variation_percent = f"+{forecast_kpis['variationPercent']:.1f}%" if forecast_kpis["variationPercent"] >= 0 else f"{forecast_kpis['variationPercent']:.1f}%"
    variation_mad = _format_mad(forecast_kpis["variation"])
    horizon = f"{forecast_kpis['horizon']} jours"
    
    col_width = (CONTENT_W - 12) / 4
    
    # Create table rows
    rows = [
        [
            Paragraph("<b>Solde actuel</b>", styles["muted"]),
            Paragraph("<b>Solde projeté</b>", styles["muted"]),
            Paragraph("<b>Variation</b>", styles["muted"]),
            Paragraph("<b>Horizon</b>", styles["muted"])
        ],
        [
            Paragraph(current_balance, styles["section"]),
            Paragraph(f"<font color='{trend_color.hexval()}'>{projected_balance}</font>", styles["section"]),
            Paragraph(f"<font color='{trend_color.hexval()}'>{variation_percent}</font> ({variation_mad})", styles["section"]),
            Paragraph(horizon, styles["section"])
        ],
        [
            "",
            "",
            Paragraph(f"<b><font color='{trend_color.hexval()}'>{trend_label}</font></b>", styles["subsection"]),
            ""
        ]
    ]
    
    table = Table(rows, colWidths=[col_width]*4)
    table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10)
    ]))
    return table


def _action_plan_table(items: list[dict], styles: dict) -> Table:
    rows = [[_p("Action", styles["th"]), _p("Responsable", styles["th"]), _p("Échéance", styles["th"])]]
    for it in items:
        rows.append([
            _p(it.get("action", ""), styles["td"]),
            _p(it.get("owner", "—"), styles["td"]),
            _p(it.get("deadline", "—"), styles["td"]),
        ])
    t = Table(rows, colWidths=[CONTENT_W * 0.58, CONTENT_W * 0.18, CONTENT_W * 0.24])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.25, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PAPER]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _draw_cover(canvas, doc, company_name: str, date_long: str, grade: str = ""):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 3 * mm, fill=1, stroke=0)
    if grade:
        canvas.setFillColor(WHITE)
        canvas.circle(PAGE_W - MARGIN_R - 12 * mm, PAGE_H - 45 * mm, 14 * mm, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(PAGE_W - MARGIN_R - 12 * mm, PAGE_H - 49 * mm, grade)
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(HexColor("#94A3B8"))
        canvas.drawCentredString(PAGE_W - MARGIN_R - 12 * mm, PAGE_H - 56 * mm, "NOTE GLOBALE")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawString(MARGIN_L, PAGE_H - 52 * mm, "Rapport de direction")
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(HexColor("#CBD5E1"))
    canvas.drawString(MARGIN_L, PAGE_H - 61 * mm, "Intelligence de trésorerie · Pilotage financier")
    canvas.setFillColor(ACCENT)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN_L, PAGE_H - 72 * mm, "DOCUMENT CONFIDENTIEL")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(MARGIN_L, PAGE_H - 98 * mm, company_name[:72])
    canvas.setFillColor(HexColor("#94A3B8"))
    canvas.setFont("Helvetica", 10)
    canvas.drawString(MARGIN_L, PAGE_H - 108 * mm, date_long)
    canvas.restoreState()


def _draw_page_frame(canvas, doc, company_name: str, date_short: str):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 13 * mm, PAGE_W, 13 * mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 13 * mm, 3.5 * mm, 13 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(MARGIN_L, PAGE_H - 9.5 * mm, "RAPPORT DE DIRECTION — TRÉSORERIE")
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 9.5 * mm, f"{company_name[:35]} · {date_short}")
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN_L, 13 * mm, PAGE_W - MARGIN_R, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 8 * mm, "Confidentiel")
    canvas.drawRightString(PAGE_W - MARGIN_R, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_executive_pdf_report(
    *,
    company_name: str,
    business_intelligence: dict,
    report_date: datetime | None = None,
    treasury_trend: str | None = None,
    previous_business_intelligence: dict | None = None,
    kpis: dict | None = None,
    forecast: list | None = None,
    locale: str = DEFAULT_LOCALE,
) -> bytes:
    locale = normalize_locale(locale)
    labels = PDF_I18N.get(locale, PDF_I18N[DEFAULT_LOCALE])
    if not business_intelligence:
        raise ValueError("business_intelligence requis")

    dt = report_date or datetime.now()
    date_long = f"{dt.day} {labels['months'][dt.month - 1]} {dt.year}"
    date_short = dt.strftime("%d/%m/%Y")
    styles = _build_styles()
    elements: list = []

    bi = business_intelligence
    health = _safe(bi, "financial_health_score", {})
    resilience = _safe(bi, "treasury_resilience_score", {}) or _safe(bi, "treasury_stress_score", {})
    runway = _safe(bi, "cash_runway", {})
    briefing = _safe(bi, "executive_briefing", {})
    risks = [r for r in (bi.get("top_risks") or []) if isinstance(r, dict)]
    decisions = [d for d in (bi.get("top_decisions") or []) if isinstance(d, dict)]

    health_score = int(_safe(health, "score", 50))
    resilience_score = int(_safe(resilience, "score", 50))
    runway_days = int(_safe(runway, "days", 30))
    health_lbl = _health_label(health_score)
    resilience_lbl = _resilience_label(resilience_score)
    treasury_balance = (kpis or {}).get("treasury_balance")
    
    # Compute chart data and forecast KPIs exactly like frontend!
    chart_data = _compute_chart_data(forecast, treasury_balance)
    forecast_kpis = _compute_forecast_kpis(chart_data, treasury_balance)
    trend = forecast_kpis["trend"]
    trend_label = {
        "up": labels["trend_up"],
        "stable": labels["trend_stable"],
        "down": labels["trend_down"],
    }.get(trend, labels["trend_stable"])
    trend_color = {
        "up": GREEN,
        "stable": NAVY,
        "down": RED
    }.get(trend, NAVY)

    grade, grade_label, composite, grade_color = _compute_global_grade(
        health_score, resilience_score, runway_days, locale
    )
    recommended = _resolve_recommended_decision(briefing, decisions, locale)
    decision_reasoning = _build_decision_reasoning(
        recommended, risks, health_score, resilience_score, runway_days, treasury_trend, locale
    )
    fin_narrative, fin_rows = _build_financial_justification(
        kpis, health_score, resilience_score, runway_days, grade, locale
    )
    plan_7, plan_30, plan_90 = _split_action_plans(briefing, decisions, locale)
    outlook = _safe(briefing, "outlook_30d", "") or _safe(briefing, "outlook_30_days", "")

    def on_page(canvas, doc):
        if doc.page == 1:
            _draw_cover(canvas, doc, company_name, date_long, grade)
        else:
            _draw_page_frame(canvas, doc, company_name, date_short)

    # —— P2 : Notation + KPI + storytelling ——
    elements.append(PageBreak())
    elements.append(_section_bar(labels["executive_view"], styles))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_grade_badge(grade, grade_label, composite, grade_color, styles))
    elements.append(Spacer(1, 4 * mm))

    hero = Table(
        [[
            _hero_kpi(labels["financial_health"], str(health_score), health_lbl, _score_color(health_score), styles),
            _hero_kpi(labels["resilience"], str(resilience_score), resilience_lbl, _score_color(resilience_score), styles),
            _hero_kpi(labels["horizon"], f"{runway_days} {labels['days_short']}", f"{max(1, runway_days // 30)} {labels['months_short']}", _score_color(min(100, runway_days // 3)), styles),
        ]],
        colWidths=[(CONTENT_W - 6) / 3 + 1] * 3,
    )
    hero.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(hero)
    elements.append(Spacer(1, 4 * mm))

    if treasury_balance is not None:
        elements.append(_callout_box([
            Paragraph(
                f"<b>{escape(labels['treasury_balance_label'])}</b> {_format_mad(treasury_balance)} "
                f"{labels['net_flow_label']}{_format_mad((kpis or {}).get('net_cashflow'))}",
                styles["callout"],
            ),
        ], bg=PAPER))
        elements.append(Spacer(1, 3 * mm))

    elements.append(_section_bar(labels["section_financial_story"], styles))
    # Note: _financial_story is still hardcoded FR for now; we'll update it if needed but the business intelligence is translated!
    elements.append(Paragraph(_financial_story(company_name, kpis, briefing, health_lbl, treasury_trend), styles["story"]))

    # —— P3 : Décision unique + raisonnement + justification ——
    elements.append(PageBreak())
    elements.append(_section_bar(labels["section_recommended_decision"], styles))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_callout_box([
        Paragraph(f"<b>{escape(labels['subsection_arbitrage'])}</b>", styles["subsection"]),
        _p(recommended.get("action", ""), styles["callout"]),
        _p(f"{escape(labels['urgency_label'])}{escape(recommended.get('urgency', '—'))}", styles["muted"]),
    ], bg=ACCENT_LIGHT))
    elements.append(Spacer(1, 3 * mm))

    elements.append(_section_bar(labels["section_decision_reasoning"], styles))
    elements.append(_p(decision_reasoning, styles["story"]))
    elements.append(Spacer(1, 3 * mm))

    elements.append(_section_bar(labels["section_financial_justification"], styles))
    elements.append(_p(fin_narrative, styles["body"]))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_financial_table(fin_rows, styles))

    # —— P4 : Analyse des prévisions de trésorerie ——
    elements.append(PageBreak())
    elements.append(_section_bar(labels["section_forecast_analysis"], styles))
    elements.append(Spacer(1, 4 * mm))
    
    # Note: _generate_forecast_narrative is still FR only; for now we'll leave it, but business intelligence is translated!
    forecast_narrative, forecast_recommendations = _generate_forecast_narrative(
        forecast_kpis, kpis, risks, decisions, briefing
    )
    
    # Ajouter le texte principal
    elements.append(_p(forecast_narrative, styles["story"]))
    elements.append(Spacer(1, 4 * mm))
    
    # Ajouter le bloc "Actions recommandées"
    elements.append(Paragraph(f"<b>{escape(labels['subsection_recommended_actions'])}</b>", styles["subsection"]))
    elements.append(Spacer(1, 2 * mm))
    for rec in forecast_recommendations:
        elements.append(Paragraph(f"• {escape(rec)}", styles["body_left"]))
        elements.append(Spacer(1, 1 * mm))

    # —— P5 : Risques métier ——
    elements.append(PageBreak())
    elements.append(_section_bar(labels["section_risks"], styles))
    elements.append(Spacer(1, 2 * mm))

    if risks:
        for i, risk in enumerate(risks[:4], 1):
            title = _safe(risk, "title", f"Risk {i}")
            sev = _safe(risk, "severity", "")
            block = KeepTogether([
                Paragraph(f"<b>{i}. {escape(title)}</b>" + (f" <font color='#64748B'>({escape(sev)})</font>" if sev != "—" else ""), styles["subsection"]),
                _p(_risk_business_narrative(risk, locale), styles["body"]),
            ])
            elements.append(block)
    else:
        elements.append(_p(labels["no_risks_message"], styles["body"]))

    main_opp = _safe(briefing, "main_opportunity", {})
    if isinstance(main_opp, dict) and _safe(main_opp, "title", ""):
        elements.append(Spacer(1, 2 * mm))
        elements.append(_callout_box([
            Paragraph(f"<b>{escape(labels['subsection_opportunity'])}</b>", styles["subsection"]),
            _p(_safe(main_opp, "title", ""), styles["callout"]),
            _p(_safe(main_opp, "description", ""), styles["muted"]),
        ], bg=ACCENT_LIGHT))

    # —— P6 : Plan d'action 7 / 30 / 90 jours ——
    elements.append(PageBreak())
    elements.append(_section_bar(labels["section_action_plan"], styles))
    elements.append(Spacer(1, 2 * mm))

    elements.append(Paragraph(f"<b>7 {escape(labels['days_short'])}</b> — {escape(labels['plan_7d_desc'])}", styles["body_left"]))
    elements.append(Spacer(1, 1.5 * mm))
    elements.append(_action_plan_table(plan_7, styles))
    elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph(f"<b>30 {escape(labels['days_short'])}</b> — {escape(labels['plan_30d_desc'])}", styles["body_left"]))
    elements.append(Spacer(1, 1.5 * mm))
    elements.append(_action_plan_table(plan_30, styles))
    elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph(f"<b>90 {escape(labels['days_short'])}</b> — {escape(labels['plan_90d_desc'])}", styles["body_left"]))
    elements.append(Spacer(1, 1.5 * mm))
    elements.append(_action_plan_table(plan_90, styles))

    # —— P7 : Clôture ——
    elements.append(PageBreak())
    elements.append(_section_bar("Synthèse de clôture", styles))
    elements.append(Spacer(1, 2 * mm))

    closing = _safe(briefing, "executive_summary", "")
    if not closing:
        closing = (
            f"Notation globale {grade} — la direction valide l'exécution du plan 7/30/90 jours "
            f"et le suivi en comité hebdomadaire."
        )
    elements.append(_p(closing, styles["story"]))

    elements.append(Spacer(1, 3 * mm))
    elements.append(_callout_box([
        _p(
            "Document d'aide à la décision — non substitut à un audit statutaire. "
            "Les projections reposent sur l'historique disponible et les hypothèses de gestion en vigueur.",
            styles["muted"],
        ),
    ], bg=PAPER))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 5 * mm,
        bottomMargin=MARGIN_B + 3 * mm,
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
    locale: str = DEFAULT_LOCALE,
) -> bytes:
    if business_intelligence:
        return generate_executive_pdf_report(
            company_name=company_name or f"Entreprise {company_id[:8]}",
            business_intelligence=business_intelligence,
            treasury_trend=(kpis or {}).get("trend"),
            previous_business_intelligence=previous_business_intelligence,
            kpis=kpis,
            forecast=forecast,
            locale=locale,
        )
    raise ValueError("Le rapport exécutif nécessite des données BI.")
