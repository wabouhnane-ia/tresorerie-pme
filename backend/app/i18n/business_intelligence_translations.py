"""Locale-safe Business Intelligence presentation payloads."""

from __future__ import annotations

from copy import deepcopy

from app.core.locale import DEFAULT_LOCALE, normalize_locale


_TEXT = {
    "fr": {
        "health": {
            "excellent": "Excellente sante financiere",
            "healthy": "Bonne sante financiere",
            "vigilance": "Vigilance",
            "fragile": "Situation fragile",
            "critical": "Situation critique",
        },
        "resilience": {
            "excellent": "Tres forte",
            "healthy": "Forte",
            "vigilance": "Moderee",
            "fragile": "Faible",
            "critical": "Critique",
        },
        "severity": {
            "Critical": "Critique",
            "High": "Elevee",
            "Medium": "Moyenne",
            "Low": "Faible",
        },
        "probability": {"high": "Elevee", "medium": "Moyenne", "low": "Faible"},
        "urgency": {"now": "Immediat", "30": "Sous 30 jours", "month": "Suivi mensuel"},
        "health_explanation": "Autonomie estimee : {months} mois. Niveau de risque global : {risk_level}.",
        "resilience_interpretation_high": "Capacite elevee a absorber un choc de tresorerie.",
        "resilience_interpretation_mid": "Situation gerable avec un pilotage regulier des flux.",
        "resilience_interpretation_low": "Marge de securite limitee : des actions de direction sont a prevoir.",
        "runway": "La tresorerie couvre environ {months} mois d'activite au rythme recent.",
        "summary": "Tresorerie avec sante {health}/100, resilience {resilience}/100 et autonomie estimee a {months} mois. Risque principal : {risk}. Decision prioritaire : {decision}.",
        "financial": "Sur les 30 derniers jours : encaissements {inflows}, depenses {outflows}, flux net {net}.",
        "cash": "Autonomie estimee {months} mois. Resilience : {label} ({score}/100).",
        "outlook": "Sur 30 jours, surveiller le solde minimum attendu et les principaux encaissements. Niveau de risque global : {risk_level}.",
        "main_risk_title": "Risque de tresorerie",
        "main_risk_desc": "La direction doit maintenir une visibilite rapprochee sur les flux et les engagements critiques.",
        "opportunity_title": "Optimiser la tresorerie",
        "opportunity_desc": "Structurer une reserve minimale et utiliser le surplus sans fragiliser les operations.",
        "decision_action": "Tenir une revue tresorerie hebdomadaire",
        "decision_rationale": "Le pilotage regulier securise la position de tresorerie et accelere la reaction aux tensions.",
        "decision_outcome": "Meilleure visibilite sur les encaissements, les depenses et les priorites de paiement.",
        "deadline": "Cette semaine",
        "alert_title": "Pilotage regulier recommande",
        "alert_desc": "Aucun signal critique immediat ; maintenir la visibilite hebdomadaire.",
        "alert_impact": "Preserver la capacite de reaction de la direction.",
        "alert_action": "Tenir une revue tresorerie hebdomadaire avec les principaux flux entrants et sortants.",
    },
    "en": {
        "health": {
            "excellent": "Excellent financial health",
            "healthy": "Healthy financial position",
            "vigilance": "Watch",
            "fragile": "Fragile situation",
            "critical": "Critical situation",
        },
        "resilience": {
            "excellent": "Very strong",
            "healthy": "Strong",
            "vigilance": "Moderate",
            "fragile": "Weak",
            "critical": "Critical",
        },
        "severity": {
            "Critical": "Critical",
            "High": "High",
            "Medium": "Medium",
            "Low": "Low",
        },
        "probability": {"high": "High", "medium": "Medium", "low": "Low"},
        "urgency": {"now": "Immediate", "30": "Within 30 days", "month": "Monitor monthly"},
        "health_explanation": "Estimated runway: {months} months. Overall risk level: {risk_level}.",
        "resilience_interpretation_high": "Strong capacity to absorb a treasury shock.",
        "resilience_interpretation_mid": "Manageable position with regular cash-flow steering.",
        "resilience_interpretation_low": "Limited safety margin: management actions should be planned.",
        "runway": "Treasury covers about {months} months of activity at the recent pace.",
        "summary": "Treasury health is {health}/100, resilience is {resilience}/100 and estimated runway is {months} months. Main risk: {risk}. Priority decision: {decision}.",
        "financial": "Over the last 30 days: inflows {inflows}, outflows {outflows}, net flow {net}.",
        "cash": "Estimated runway is {months} months. Resilience: {label} ({score}/100).",
        "outlook": "Over 30 days, monitor the expected low balance and the main incoming cash flows. Overall risk level: {risk_level}.",
        "main_risk_title": "Treasury risk",
        "main_risk_desc": "Management should keep close visibility over cash flows and critical commitments.",
        "opportunity_title": "Optimize treasury",
        "opportunity_desc": "Structure a minimum reserve and use surplus cash without weakening operations.",
        "decision_action": "Run a weekly treasury review",
        "decision_rationale": "Regular steering protects the treasury position and speeds up the response to pressure.",
        "decision_outcome": "Better visibility over collections, spending and payment priorities.",
        "deadline": "This week",
        "alert_title": "Regular steering recommended",
        "alert_desc": "No immediate critical signal; keep weekly visibility.",
        "alert_impact": "Preserve management's ability to react.",
        "alert_action": "Run a weekly treasury review with the main inflows and outflows.",
    },
    "ar": {
        "health": {
            "excellent": "\u0635\u062d\u0629 \u0645\u0627\u0644\u064a\u0629 \u0645\u0645\u062a\u0627\u0632\u0629",
            "healthy": "\u0648\u0636\u0639 \u0645\u0627\u0644\u064a \u062c\u064a\u062f",
            "vigilance": "\u064a\u062a\u0637\u0644\u0628 \u0627\u0644\u0645\u062a\u0627\u0628\u0639\u0629",
            "fragile": "\u0648\u0636\u0639 \u0647\u0634",
            "critical": "\u0648\u0636\u0639 \u062d\u0631\u062c",
        },
        "resilience": {
            "excellent": "\u0642\u0648\u064a\u0629 \u062c\u062f\u0627",
            "healthy": "\u0642\u0648\u064a\u0629",
            "vigilance": "\u0645\u062a\u0648\u0633\u0637\u0629",
            "fragile": "\u0636\u0639\u064a\u0641\u0629",
            "critical": "\u062d\u0631\u062c\u0629",
        },
        "severity": {
            "Critical": "\u062d\u0631\u062c",
            "High": "\u0645\u0631\u062a\u0641\u0639",
            "Medium": "\u0645\u062a\u0648\u0633\u0637",
            "Low": "\u0645\u0646\u062e\u0641\u0636",
        },
        "probability": {"high": "\u0645\u0631\u062a\u0641\u0639\u0629", "medium": "\u0645\u062a\u0648\u0633\u0637\u0629", "low": "\u0645\u0646\u062e\u0641\u0636\u0629"},
        "urgency": {"now": "\u0641\u0648\u0631\u064a", "30": "\u062e\u0644\u0627\u0644 30 \u064a\u0648\u0645\u0627", "month": "\u0645\u062a\u0627\u0628\u0639\u0629 \u0634\u0647\u0631\u064a\u0629"},
        "health_explanation": "\u0627\u0644\u0623\u0641\u0642 \u0627\u0644\u0645\u0642\u062f\u0631: {months} \u0634\u0647\u0631. \u0645\u0633\u062a\u0648\u0649 \u0627\u0644\u0645\u062e\u0627\u0637\u0631: {risk_level}.",
        "resilience_interpretation_high": "\u0642\u062f\u0631\u0629 \u0642\u0648\u064a\u0629 \u0639\u0644\u0649 \u0627\u0645\u062a\u0635\u0627\u0635 \u0635\u062f\u0645\u0629 \u0641\u064a \u0627\u0644\u062e\u0632\u064a\u0646\u0629.",
        "resilience_interpretation_mid": "\u0648\u0636\u0639 \u0642\u0627\u0628\u0644 \u0644\u0644\u062a\u0633\u064a\u064a\u0631 \u0645\u0639 \u0645\u062a\u0627\u0628\u0639\u0629 \u0645\u0646\u062a\u0638\u0645\u0629 \u0644\u0644\u062a\u062f\u0641\u0642\u0627\u062a.",
        "resilience_interpretation_low": "\u0647\u0627\u0645\u0634 \u0623\u0645\u0627\u0646 \u0645\u062d\u062f\u0648\u062f: \u064a\u062c\u0628 \u062a\u062e\u0637\u064a\u0637 \u0625\u062c\u0631\u0627\u0621\u0627\u062a \u0627\u0644\u0625\u062f\u0627\u0631\u0629.",
        "runway": "\u062a\u063a\u0637\u064a \u0627\u0644\u062e\u0632\u064a\u0646\u0629 \u062d\u0648\u0627\u0644\u064a {months} \u0634\u0647\u0631 \u0645\u0646 \u0627\u0644\u0646\u0634\u0627\u0637 \u0628\u0627\u0644\u0648\u062a\u064a\u0631\u0629 \u0627\u0644\u062d\u0627\u0644\u064a\u0629.",
        "summary": "\u0635\u062d\u0629 \u0627\u0644\u062e\u0632\u064a\u0646\u0629 {health}/100\u060c \u0648\u0627\u0644\u0645\u0631\u0648\u0646\u0629 {resilience}/100\u060c \u0648\u0627\u0644\u0623\u0641\u0642 \u0627\u0644\u0645\u0642\u062f\u0631 {months} \u0634\u0647\u0631. \u0627\u0644\u062e\u0637\u0631 \u0627\u0644\u0631\u0626\u064a\u0633\u064a: {risk}. \u0627\u0644\u0642\u0631\u0627\u0631 \u0627\u0644\u0623\u0648\u0644\u0648\u064a: {decision}.",
        "financial": "\u062e\u0644\u0627\u0644 \u0622\u062e\u0631 30 \u064a\u0648\u0645\u0627: \u0627\u0644\u062a\u062d\u0635\u064a\u0644\u0627\u062a {inflows}\u060c \u0627\u0644\u0645\u0635\u0627\u0631\u064a\u0641 {outflows}\u060c \u0635\u0627\u0641\u064a \u0627\u0644\u062a\u062f\u0641\u0642 {net}.",
        "cash": "\u0627\u0644\u0623\u0641\u0642 \u0627\u0644\u0645\u0642\u062f\u0631 {months} \u0634\u0647\u0631. \u0627\u0644\u0645\u0631\u0648\u0646\u0629: {label} ({score}/100).",
        "outlook": "\u062e\u0644\u0627\u0644 30 \u064a\u0648\u0645\u0627\u060c \u0631\u0627\u0642\u0628 \u0623\u062f\u0646\u0649 \u0631\u0635\u064a\u062f \u0645\u062a\u0648\u0642\u0639 \u0648\u0623\u0647\u0645 \u0627\u0644\u062a\u062d\u0635\u064a\u0644\u0627\u062a. \u0645\u0633\u062a\u0648\u0649 \u0627\u0644\u0645\u062e\u0627\u0637\u0631: {risk_level}.",
        "main_risk_title": "\u0645\u062e\u0627\u0637\u0631 \u0627\u0644\u062e\u0632\u064a\u0646\u0629",
        "main_risk_desc": "\u064a\u062c\u0628 \u0639\u0644\u0649 \u0627\u0644\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u062d\u0641\u0627\u0638 \u0639\u0644\u0649 \u0631\u0624\u064a\u0629 \u0642\u0631\u064a\u0628\u0629 \u0644\u0644\u062a\u062f\u0641\u0642\u0627\u062a \u0648\u0627\u0644\u0627\u0644\u062a\u0632\u0627\u0645\u0627\u062a \u0627\u0644\u062d\u0631\u062c\u0629.",
        "opportunity_title": "\u062a\u062d\u0633\u064a\u0646 \u0627\u0644\u062e\u0632\u064a\u0646\u0629",
        "opportunity_desc": "\u0647\u064a\u0643\u0644\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a \u0623\u062f\u0646\u0649 \u0648\u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0627\u0644\u0641\u0627\u0626\u0636 \u062f\u0648\u0646 \u0625\u0636\u0639\u0627\u0641 \u0627\u0644\u0639\u0645\u0644\u064a\u0627\u062a.",
        "decision_action": "\u0625\u062c\u0631\u0627\u0621 \u0645\u0631\u0627\u062c\u0639\u0629 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 \u0644\u0644\u062e\u0632\u064a\u0646\u0629",
        "decision_rationale": "\u0627\u0644\u062a\u0633\u064a\u064a\u0631 \u0627\u0644\u0645\u0646\u062a\u0638\u0645 \u064a\u062d\u0645\u064a \u0648\u0636\u0639 \u0627\u0644\u062e\u0632\u064a\u0646\u0629 \u0648\u064a\u0633\u0631\u0639 \u0627\u0644\u062a\u0641\u0627\u0639\u0644 \u0645\u0639 \u0627\u0644\u0636\u063a\u0637.",
        "decision_outcome": "\u0631\u0624\u064a\u0629 \u0623\u0641\u0636\u0644 \u0644\u0644\u062a\u062d\u0635\u064a\u0644\u0627\u062a \u0648\u0627\u0644\u0645\u0635\u0627\u0631\u064a\u0641 \u0648\u0623\u0648\u0644\u0648\u064a\u0627\u062a \u0627\u0644\u062f\u0641\u0639.",
        "deadline": "\u0647\u0630\u0627 \u0627\u0644\u0623\u0633\u0628\u0648\u0639",
        "alert_title": "\u064a\u0648\u0635\u0649 \u0628\u062a\u0633\u064a\u064a\u0631 \u0645\u0646\u062a\u0638\u0645",
        "alert_desc": "\u0644\u0627 \u062a\u0648\u062c\u062f \u0625\u0634\u0627\u0631\u0629 \u062d\u0631\u062c\u0629 \u0641\u0648\u0631\u064a\u0629\u061b \u062d\u0627\u0641\u0638 \u0639\u0644\u0649 \u0631\u0624\u064a\u0629 \u0623\u0633\u0628\u0648\u0639\u064a\u0629.",
        "alert_impact": "\u0627\u0644\u062d\u0641\u0627\u0638 \u0639\u0644\u0649 \u0642\u062f\u0631\u0629 \u0627\u0644\u0625\u062f\u0627\u0631\u0629 \u0639\u0644\u0649 \u0627\u0644\u062a\u0641\u0627\u0639\u0644.",
        "alert_action": "\u0625\u062c\u0631\u0627\u0621 \u0645\u0631\u0627\u062c\u0639\u0629 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 \u0644\u0644\u062e\u0632\u064a\u0646\u0629 \u0645\u0639 \u0623\u0647\u0645 \u0627\u0644\u062a\u062f\u0641\u0642\u0627\u062a \u0627\u0644\u062f\u0627\u062e\u0644\u0629 \u0648\u0627\u0644\u062e\u0627\u0631\u062c\u0629.",
    },
}


def _catalog(locale: str) -> dict:
    return _TEXT.get(normalize_locale(locale), _TEXT[DEFAULT_LOCALE])


def _money(value: float | int | None) -> str:
    return f"{float(value or 0):,.0f} MAD"


def _risk_level(payload: dict) -> str:
    for path in (
        ("executive_briefing", "main_risk", "severity"),
        ("top_risks", 0, "severity"),
    ):
        cur = payload
        for part in path:
            if isinstance(part, int):
                cur = cur[part] if isinstance(cur, list) and len(cur) > part else None
            else:
                cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur:
            return str(cur)
    return "LOW"


def localize_business_intelligence_payload(payload: dict | None, locale: str = DEFAULT_LOCALE) -> dict | None:
    """Overwrite user-facing BI prose with locale-specific deterministic content."""

    loc = normalize_locale(locale)
    if not isinstance(payload, dict) or loc == DEFAULT_LOCALE:
        return payload

    text = _catalog(loc)
    out = deepcopy(payload)
    health = out.get("financial_health_score") or {}
    resilience = out.get("treasury_resilience_score") or {}
    runway = out.get("cash_runway") or {}
    score = int(health.get("score") or 0)
    res_score = int(resilience.get("score") or 0)
    months = runway.get("months", 0)
    risk_level = _risk_level(out)

    health_category = health.get("category") or "vigilance"
    health["label"] = text["health"].get(health_category, text["health"]["vigilance"])
    health["explanation"] = text["health_explanation"].format(months=months, risk_level=risk_level)

    res_category = resilience.get("category") or "vigilance"
    resilience["label"] = text["resilience"].get(res_category, text["resilience"]["vigilance"])
    if res_score >= 75:
        resilience["interpretation"] = text["resilience_interpretation_high"]
    elif res_score < 60:
        resilience["interpretation"] = text["resilience_interpretation_low"]
    else:
        resilience["interpretation"] = text["resilience_interpretation_mid"]
    resilience["drivers"] = [
        text["cash"].format(months=months, label=resilience["label"], score=res_score)
    ]

    runway["interpretation"] = text["runway"].format(months=months)

    for alert in out.get("smart_alerts") or []:
        if not isinstance(alert, dict):
            continue
        severity = str(alert.get("severity") or "Low")
        alert["severity"] = text["severity"].get(severity, severity)
        alert["title"] = text["alert_title"]
        alert["description"] = text["alert_desc"]
        alert["business_impact"] = text["alert_impact"]
        alert["recommended_action"] = text["alert_action"]
        alert["management_focus"] = alert["description"]

    for risk in out.get("top_risks") or []:
        if not isinstance(risk, dict):
            continue
        severity = str(risk.get("severity") or "Medium")
        risk["title"] = text["main_risk_title"]
        risk["severity"] = text["severity"].get(severity, severity)
        risk["probability"] = text["probability"]["medium"]
        risk["impact"] = text["main_risk_desc"]
        risk["recommended_action"] = text["decision_action"]
        risk["urgency"] = text["urgency"]["30"]

    for decision in out.get("top_decisions") or []:
        if not isinstance(decision, dict):
            continue
        decision["action"] = text["decision_action"]
        decision["expected_benefit"] = text["decision_outcome"]
        decision["urgency"] = text["urgency"]["30"]
        decision["business_justification"] = text["decision_rationale"]
        decision["time_horizon"] = text["urgency"]["30"]

    briefing = out.get("executive_briefing") or {}
    if isinstance(briefing, dict):
        inflows = _money((runway.get("avg_daily_inflow") or 0) * 30)
        outflows = _money((runway.get("avg_daily_outflow") or 0) * 30)
        net = _money((runway.get("avg_daily_net") or 0) * 30)
        briefing["executive_summary"] = text["summary"].format(
            health=score,
            resilience=res_score,
            months=months,
            risk=text["main_risk_title"],
            decision=text["decision_action"],
        )
        briefing["executive_briefing"] = briefing["executive_summary"]
        briefing["financial_situation"] = text["financial"].format(
            inflows=inflows,
            outflows=outflows,
            net=net,
        )
        briefing["cash_position_analysis"] = text["cash"].format(
            months=months,
            label=resilience["label"],
            score=res_score,
        )
        briefing["outlook_30_days"] = text["outlook"].format(risk_level=risk_level)
        briefing["main_risk"] = {
            "title": text["main_risk_title"],
            "description": text["main_risk_desc"],
            "severity": text["severity"].get("Medium"),
            "estimated_financial_impact": _money((runway.get("avg_daily_outflow") or 0) * 30),
        }
        briefing["main_opportunity"] = {
            "title": text["opportunity_title"],
            "description": text["opportunity_desc"],
            "potential_benefit": text["decision_outcome"],
        }
        briefing["recommended_decision"] = {
            "action": text["decision_action"],
            "rationale": text["decision_rationale"],
            "expected_outcome": text["decision_outcome"],
            "urgency": text["urgency"]["30"],
        }
        briefing["immediate_actions"] = [
            {
                "action": text["decision_action"],
                "why": text["decision_rationale"],
                "deadline": text["deadline"],
            }
        ]

    return out
