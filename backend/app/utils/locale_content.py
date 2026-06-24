"""Normalize and label API business content per user locale (fr, en, ar)."""

from __future__ import annotations

from app.core.locale import DEFAULT_LOCALE, normalize_locale

_LABELS = {
    "fr": {
        "severity": {
            "critical": "Critique",
            "high": "Élevée",
            "medium": "Moyenne",
            "low": "Faible",
        },
        "priority": {
            "critical": "Critique",
            "high": "Élevée",
            "medium": "Moyenne",
            "low": "Faible",
        },
        "difficulty": {
            "easy": "Facile",
            "medium": "Moyen",
            "hard": "Difficile",
        },
        "urgency": {
            "immediate": "Immédiat",
            "within 7 days": "Sous 7 jours",
            "within 15 days": "Sous 15 jours",
            "within 30 days": "Sous 30 jours",
            "monitor monthly": "Suivi mensuel",
            "high": "Élevée",
            "medium": "Moyenne",
            "low": "Faible",
        },
        "probability": {"high": "Élevée", "medium": "Moyenne", "low": "Faible"},
        "category": {
            "liquidity": "Liquidité",
            "working capital": "Fonds de roulement",
            "cost control": "Maîtrise des coûts",
            "cash optimization": "Optimisation de trésorerie",
            "revenue protection": "Protection des encaissements",
        },
        "time_horizon": {
            "next 30 days": "Prochains 30 jours",
            "0-7 days": "0-7 jours",
            "7-30 days": "7-30 jours",
            "0-15 days": "0-15 jours",
            "15-30 days": "15-30 jours",
            "0-30 days": "0-30 jours",
            "30-90 days": "30-90 jours",
        },
        "risk_titles": {
            "liquidity risk": "Risque de liquidité",
            "cashflow risk": "Risque de flux de trésorerie",
            "revenue risk": "Risque sur les encaissements",
            "expense inflation risk": "Risque d'inflation des dépenses",
            "volatility risk": "Risque de volatilité",
            "forecast deterioration risk": "Risque de dégradation des perspectives",
        },
        "disclaimer": "Aide à la décision — ne constitue pas un conseil financier réglementé.",
    },
    "en": {
        "severity": {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        },
        "priority": {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        },
        "difficulty": {"easy": "Easy", "medium": "Medium", "hard": "Hard"},
        "urgency": {
            "immediate": "Immediate",
            "within 7 days": "Within 7 days",
            "within 15 days": "Within 15 days",
            "within 30 days": "Within 30 days",
            "monitor monthly": "Monitor monthly",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        },
        "probability": {"high": "High", "medium": "Medium", "low": "Low"},
        "category": {
            "liquidity": "Liquidity",
            "working capital": "Working capital",
            "cost control": "Cost control",
            "cash optimization": "Cash optimization",
            "revenue protection": "Revenue protection",
        },
        "time_horizon": {
            "next 30 days": "Next 30 days",
            "0-7 days": "0-7 days",
            "7-30 days": "7-30 days",
            "0-15 days": "0-15 days",
            "15-30 days": "15-30 days",
            "0-30 days": "0-30 days",
            "30-90 days": "30-90 days",
        },
        "risk_titles": {
            "liquidity risk": "Liquidity risk",
            "cashflow risk": "Cashflow risk",
            "revenue risk": "Revenue risk",
            "expense inflation risk": "Expense inflation risk",
            "volatility risk": "Volatility risk",
            "forecast deterioration risk": "Forecast deterioration risk",
        },
        "disclaimer": "Decision support only — not regulated financial advice.",
    },
    "ar": {
        "severity": {
            "critical": "حرج",
            "high": "مرتفع",
            "medium": "متوسط",
            "low": "منخفض",
        },
        "priority": {
            "critical": "حرج",
            "high": "مرتفع",
            "medium": "متوسط",
            "low": "منخفض",
        },
        "difficulty": {"easy": "سهل", "medium": "متوسط", "hard": "صعب"},
        "urgency": {
            "immediate": "فوري",
            "within 7 days": "خلال 7 أيام",
            "within 15 days": "خلال 15 يوماً",
            "within 30 days": "خلال 30 يوماً",
            "monitor monthly": "متابعة شهرية",
            "high": "مرتفع",
            "medium": "متوسط",
            "low": "منخفض",
        },
        "probability": {"high": "مرتفعة", "medium": "متوسطة", "low": "منخفضة"},
        "category": {
            "liquidity": "السيولة",
            "working capital": "رأس المال العامل",
            "cost control": "ضبط التكاليف",
            "cash optimization": "تحسين النقد",
            "revenue protection": "حماية التحصيلات",
        },
        "time_horizon": {
            "next 30 days": "الـ 30 يوماً القادمة",
            "0-7 days": "0-7 أيام",
            "7-30 days": "7-30 يوماً",
            "0-15 days": "0-15 يوماً",
            "15-30 days": "15-30 يوماً",
            "0-30 days": "0-30 يوماً",
            "30-90 days": "30-90 يوماً",
        },
        "risk_titles": {
            "liquidity risk": "مخاطر السيولة",
            "cashflow risk": "مخاطر التدفق النقدي",
            "revenue risk": "مخاطر التحصيل",
            "expense inflation risk": "مخاطر ارتفاع المصاريف",
            "volatility risk": "مخاطر التقلب",
            "forecast deterioration risk": "مخاطر تدهور الآفاق",
        },
        "disclaimer": "مساعدة للقرار — لا يُعدّ نصيحة مالية منظّمة.",
    },
}

# Canonical keys for cross-locale title matching
_RISK_CANONICAL = {
    "risque de liquidité": "liquidity risk",
    "liquidity risk": "liquidity risk",
    "risque de flux de trésorerie": "cashflow risk",
    "cashflow risk": "cashflow risk",
    "risque sur les encaissements": "revenue risk",
    "revenue risk": "revenue risk",
    "risque d'inflation des dépenses": "expense inflation risk",
    "expense inflation risk": "expense inflation risk",
    "risque de volatilité": "volatility risk",
    "volatility risk": "volatility risk",
    "risque de dégradation des perspectives": "forecast deterioration risk",
    "forecast deterioration risk": "forecast deterioration risk",
    "مخاطر السيولة": "liquidity risk",
    "مخاطر التدفق النقدي": "cashflow risk",
}


def _labels(locale: str) -> dict:
    return _LABELS.get(normalize_locale(locale), _LABELS[DEFAULT_LOCALE])


def _map_value(value: str | None, mapping: dict[str, str]) -> str | None:
    if not isinstance(value, str):
        return value
    return mapping.get(value.strip().lower(), value)


def normalize_time_horizon(value: str | None, locale: str = DEFAULT_LOCALE) -> str | None:
    if not isinstance(value, str):
        return value
    th_map = _labels(locale).get("time_horizon", {})
    key = value.strip().lower()
    if key in th_map:
        return th_map[key]
    text = value
    if locale == "fr":
        for old, new in (
            ("Next 30 days", "Prochains 30 jours"),
            ("Next ", "Prochains "),
            (" days", " jours"),
            (" day", " jour"),
        ):
            text = text.replace(old, new)
    return text


def normalize_recommendation_item(item: dict, locale: str = DEFAULT_LOCALE) -> dict:
    loc = normalize_locale(locale)
    lab = _labels(loc)
    out = dict(item)
    out["severity"] = _map_value(out.get("severity"), lab["severity"]) or out.get("severity")
    out["priority"] = _map_value(out.get("priority"), lab["priority"]) or out.get("priority")
    out["difficulty"] = _map_value(out.get("difficulty"), lab["difficulty"]) or out.get("difficulty")
    out["probability"] = _map_value(out.get("probability"), lab.get("probability", {})) or out.get(
        "probability"
    )
    cat_key = str(out.get("category", "")).strip().lower()
    out["category"] = lab["category"].get(cat_key, out.get("category"))
    out["time_horizon"] = normalize_time_horizon(out.get("time_horizon"), loc)
    return out


def normalize_risk_entry(risk: dict, locale: str = DEFAULT_LOCALE) -> dict:
    loc = normalize_locale(locale)
    lab = _labels(loc)
    out = dict(risk)
    title = out.get("title")
    if isinstance(title, str):
        canon = _RISK_CANONICAL.get(title.strip().lower())
        if canon:
            out["title"] = lab["risk_titles"].get(canon, title)
    out["severity"] = _map_value(out.get("severity"), lab["severity"]) or out.get("severity")
    out["probability"] = _map_value(out.get("probability"), lab["probability"]) or out.get(
        "probability"
    )
    out["urgency"] = _map_value(out.get("urgency"), lab["urgency"]) or out.get("urgency")
    return out


def normalize_risk_intelligence(risk_intel: dict | None, locale: str = DEFAULT_LOCALE) -> dict:
    if not isinstance(risk_intel, dict):
        return risk_intel or {}
    out = dict(risk_intel)
    top_risks = out.get("top_risks") or []
    out["top_risks"] = [
        normalize_risk_entry(r, locale) for r in top_risks if isinstance(r, dict)
    ]
    return out


def normalize_executive_analysis(analysis: dict | None, locale: str = DEFAULT_LOCALE) -> dict | None:
    if not isinstance(analysis, dict):
        return analysis

    loc = normalize_locale(locale)
    lab = _labels(loc)
    out = dict(analysis)
    main_risk = out.get("main_risk")
    if isinstance(main_risk, dict):
        mr = normalize_risk_entry(
            {**main_risk, "title": main_risk.get("title", ""), "urgency": main_risk.get("urgency")},
            loc,
        )
        out["main_risk"] = mr

    rec_dec = out.get("recommended_decision")
    if isinstance(rec_dec, dict):
        rd = dict(rec_dec)
        rd["urgency"] = _map_value(rd.get("urgency"), lab["urgency"]) or rd.get("urgency")
        out["recommended_decision"] = rd

    actions = out.get("immediate_actions") or []
    normalized_actions = []
    for action in actions:
        if not isinstance(action, dict):
            normalized_actions.append(action)
            continue
        a = dict(action)
        a["deadline"] = normalize_time_horizon(a.get("deadline"), loc)
        normalized_actions.append(a)
    out["immediate_actions"] = normalized_actions
    return out


def disclaimer_for_locale(locale: str) -> str:
    return _labels(locale).get("disclaimer", _LABELS[DEFAULT_LOCALE]["disclaimer"])
