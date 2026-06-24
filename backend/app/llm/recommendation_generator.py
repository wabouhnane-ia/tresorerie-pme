"""Executive Digital CFO analysis generator.

The LLM is optional. The deterministic fallback is the source of resilience and
uses only treasury context, risk rules, recommendations, and forecast outputs.
"""

import json
import logging
import re
from datetime import datetime

from openai import OpenAI

from app.core.config import settings
from app.services.financial_narrative_generator import FinancialNarrativeGenerator
from app.core.locale import DEFAULT_LOCALE, normalize_locale
from app.utils.locale_content import normalize_executive_analysis

logger = logging.getLogger(__name__)


client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


SYSTEM_PROMPTS = {
    "fr": """
Tu es un CFO digital pour dirigeants de PME marocaines.
Tu produis un briefing de direction actionnable, en francais professionnel simple.
Interdit : jargon technique, IA, modeles, Prophet, LSTM, RMSE, MAE, MAPE, machine learning.
Reponds uniquement en JSON valide, sans markdown ni texte hors schema.
N'invente aucun chiffre : utilise uniquement le contexte fourni.

Schema exact :
{
  "executive_summary": "3-5 phrases : position, evolution, risque cle, opportunite, decision.",
  "financial_situation": "Encaissements, depenses, flux net et tendance sur la periode fournie.",
  "main_risk": {
    "title": "",
    "description": "",
    "severity": "Faible | Moyenne | Élevée | Critique",
    "estimated_financial_impact": "Montant ou fourchette en MAD si possible"
  },
  "main_opportunity": {
    "title": "",
    "description": "",
    "potential_benefit": ""
  },
  "cash_position_analysis": "Solde, autonomie estimee, marge de securite — chiffres reels.",
  "outlook_30_days": "Ce qui peut se passer sur 30 jours et ce que le dirigeant doit surveiller.",
  "recommended_decision": {
    "action": "Une decision claire",
    "rationale": "Pourquoi maintenant",
    "expected_outcome": "Benefice attendu",
    "urgency": "Immédiat | Élevée | Moyenne | Faible"
  },
  "immediate_actions": [
    {"action": "", "why": "", "deadline": "Cette semaine | 30 jours"}
  ]
}

Chaque phrase doit citer ou refleter les donnees du contexte. Pas de formules generiques.
""",
    "en": """
You are a digital CFO for SME executives in Morocco.
Produce an actionable executive briefing in clear professional English.
Forbidden: technical jargon, AI, models, Prophet, LSTM, RMSE, MAE, MAPE, machine learning.
Respond only with valid JSON, no markdown or text outside the schema.
Do not invent figures: use only the provided context.

Exact schema:
{
  "executive_summary": "3-5 sentences: position, trend, key risk, opportunity, decision.",
  "financial_situation": "Inflows, outflows, net flow and trend for the period provided.",
  "main_risk": {
    "title": "",
    "description": "",
    "severity": "Low | Medium | High | Critical",
    "estimated_financial_impact": "Amount or range in MAD if possible"
  },
  "main_opportunity": {
    "title": "",
    "description": "",
    "potential_benefit": ""
  },
  "cash_position_analysis": "Balance, estimated runway, safety margin — real figures.",
  "outlook_30_days": "What may happen over 30 days and what the executive should watch.",
  "recommended_decision": {
    "action": "A clear decision",
    "rationale": "Why now",
    "expected_outcome": "Expected benefit",
    "urgency": "Immediate | High | Medium | Low"
  },
  "immediate_actions": [
    {"action": "", "why": "", "deadline": "This week | 30 days"}
  ]
}

Every sentence must reflect the context data. No generic filler.
""",
    "ar": """
أنت مدير مالي رقمي لمسيري شركات صغيرة ومتوسطة في المغرب.
أنتج إحاطة تنفيذية قابلة للتنفيذ بالعربية الفصحى المهنية البسيطة.
ممنوع: المصطلحات التقنية، الذكاء الاصطناعي، النماذج، Prophet، LSTM، RMSE، MAE، MAPE، التعلم الآلي.
أجب فقط بـ JSON صالح، دون markdown أو نص خارج المخطط.
لا تخترع أرقاماً: استخدم السياق المقدم فقط.

المخطط:
{
  "executive_summary": "3-5 جمل: الوضع، الاتجاه، الخطر الرئيسي، الفرصة، القرار.",
  "financial_situation": "التحصيلات، المصاريف، صافي التدفق والاتجاه.",
  "main_risk": {
    "title": "",
    "description": "",
    "severity": "منخفض | متوسط | مرتفع | حرج",
    "estimated_financial_impact": "مبلغ أو نطاق بالدرهم إن أمكن"
  },
  "main_opportunity": {
    "title": "",
    "description": "",
    "potential_benefit": ""
  },
  "cash_position_analysis": "الرصيد، الأفق، هامش الأمان — أرقام حقيقية.",
  "outlook_30_days": "ما قد يحدث خلال 30 يوماً وما يجب مراقبته.",
  "recommended_decision": {
    "action": "قرار واضح",
    "rationale": "لماذا الآن",
    "expected_outcome": "النتيجة المتوقعة",
    "urgency": "فوري | مرتفع | متوسط | منخفض"
  },
  "immediate_actions": [
    {"action": "", "why": "", "deadline": "هذا الأسبوع | 30 يوماً"}
  ]
}

كل جملة يجب أن تعكس بيانات السياق.
""",
}


def _sanitize_llm_response(text: str) -> str:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _json_serializer(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _format_mad(value: float) -> str:
    return f"{float(value or 0):,.0f} MAD"


def _rule_based_fallback(context: dict) -> dict:
    """Production fallback executive analysis using real data only."""

    treasury_balance = float(context.get("treasury_balance") or 0)
    avg_cashflow = float(context.get("avg_daily_cashflow") or 0)
    forecast_trend = context.get("forecast_trend", "unknown")
    predicted_negative_day = context.get("days_until_zero")
    forecast_min_balance = float(context.get("forecast_min_balance_30d") or treasury_balance)
    volatility = float(context.get("forecast_volatility") or 0)
    risk_level = (context.get("risk_level") or "low").lower()
    liquidity_stress = float(context.get("liquidity_stress") or 0)
    risk_intelligence = context.get("risk_intelligence") or {}
    recommendations = context.get("recommendations") or []

    if risk_intelligence.get("global_risk_level"):
        risk_label = risk_intelligence["global_risk_level"]
    elif predicted_negative_day is not None and predicted_negative_day <= 7:
        risk_label = "CRITICAL"
    elif predicted_negative_day is not None and predicted_negative_day <= 30:
        risk_label = "HIGH"
    elif risk_level == "high" or liquidity_stress >= 0.8:
        risk_label = "HIGH"
    elif risk_level == "medium" or liquidity_stress >= 0.5:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"

    risk_score = int(risk_intelligence.get("global_risk_score") or 15)
    if avg_cashflow < 0:
        risk_score += 20
    if predicted_negative_day and predicted_negative_day <= 30:
        risk_score += 30
    if volatility > 20000:
        risk_score += 10
    risk_score = min(100, max(0, risk_score))

    strengths = []
    if treasury_balance > 0:
        strengths.append(f"Tresorerie positive de {_format_mad(treasury_balance)}.")
    if treasury_balance >= abs(avg_cashflow) * 30 and avg_cashflow != 0:
        strengths.append("Reserve de liquidite suffisante pour absorber le rythme recent des flux.")
    if avg_cashflow >= 0:
        strengths.append(f"Generation de cash operationnel positive a {_format_mad(avg_cashflow)} par jour.")
    if forecast_trend in {"stable", "improving"}:
        strengths.append(f"Evolution de tresorerie {forecast_trend}, sans deterioration immediate detectee.")
    if volatility <= 20000:
        strengths.append("Flux relativement stables, ce qui facilite la planification de court terme.")
    if not strengths:
        strengths.append("La situation reste pilotable avec une surveillance rapprochee des flux.")

    vigilance = []
    if avg_cashflow < 0:
        vigilance.append(f"Flux net moyen negatif de {_format_mad(avg_cashflow)} par jour.")
    if forecast_trend == "declining":
        vigilance.append("Tendance de tresorerie en deterioration sur l'horizon analyse.")
    if predicted_negative_day is not None and predicted_negative_day <= 30:
        vigilance.append(f"Point de tension possible dans environ {predicted_negative_day} jours.")
    if forecast_min_balance < treasury_balance:
        vigilance.append(f"Point bas projete a {_format_mad(forecast_min_balance)} sur 30 jours.")
    if volatility > 20000:
        vigilance.append(f"Volatilite elevee des flux autour de {_format_mad(volatility)}.")
    if not vigilance:
        vigilance.append("Aucun point de vigilance majeur, mais les encaissements et depenses critiques doivent rester suivis.")

    primary_rec = recommendations[0] if recommendations else {}
    decision_title = primary_rec.get("title") or (
        "Optimiser l'allocation de trésorerie excédentaire" if risk_label == "LOW" else "Renforcer la trésorerie disponible"
    )
    decision_why = primary_rec.get("why") or primary_rec.get("reasoning") or (
        "La position actuelle permet d'ameliorer le rendement de la tresorerie sans reduire la reserve operationnelle."
        if risk_label == "LOW"
        else "La trajectoire de tresorerie impose de proteger les engagements critiques et d'accelerer les encaissements."
    )
    decision_impact = primary_rec.get("expected_impact") or primary_rec.get("business_impact") or (
        "Meilleure allocation du cash disponible."
        if risk_label == "LOW"
        else "Reduction du risque de tension de liquidite a court terme."
    )
    decision_horizon = primary_rec.get("time_horizon") or ("30-90 jours" if risk_label == "LOW" else "0-30 jours")

    top_risks = risk_intelligence.get("top_risks") or []
    main_risk = top_risks[0] if top_risks else {}
    main_risk_description = main_risk.get("description") or (
        "Risque limite: la direction doit surtout maintenir la discipline de suivi."
        if risk_label == "LOW"
        else "Risque de tension sur les flux de tresorerie operationnels."
    )
    opportunity_description = (
        "Optimisation du rendement de l'excedent de tresorerie."
        if risk_label == "LOW"
        else "Acceleration des encaissements clients et meilleure discipline des paiements."
    )

    runway = context.get("cash_runway") or {}
    runway_months = runway.get("months", "N/A")
    last_inflows = float(context.get("last_30d_inflows") or 0)
    last_outflows = float(context.get("last_30d_outflows") or 0)
    last_net = float(context.get("last_30d_net") or 0)

    severity = "Critique" if risk_label == "CRITICAL" else "Élevé" if risk_label == "HIGH" else "Moyen" if risk_label == "MEDIUM" else "Faible"
    impact_est = main_risk.get("estimated_financial_impact") or (
        f"Jusqu'à {_format_mad(abs(avg_cashflow) * 30)} sur 30 jours si la consommation se poursuit."
        if avg_cashflow < 0
        else f"Réserve actuelle {_format_mad(treasury_balance)}."
    )

    executive_summary = " ".join(
        [
            f"Trésorerie à {_format_mad(treasury_balance)} avec autonomie estimée de {runway_months} mois.",
            f"Flux net moyen : {_format_mad(avg_cashflow)} par jour, tendance {forecast_trend}.",
            f"Risque principal : {main_risk.get('title', main_risk_description)}.",
            f"Opportunité : {opportunity_description}",
            f"Décision recommandée : {decision_title}.",
        ]
    )

    analysis = {
        "executive_summary": executive_summary,
        "executive_briefing": executive_summary,
        "financial_situation": (
            f"Encaissements 30j : {_format_mad(last_inflows)}, dépenses 30j : {_format_mad(last_outflows)}, "
            f"flux net 30j : {_format_mad(last_net)}. Solde {_format_mad(treasury_balance)}, "
            f"flux journalier moyen {_format_mad(avg_cashflow)}."
        ),
        "main_risk": {
            "title": main_risk.get("title", "Risque de trésorerie"),
            "description": main_risk_description,
            "severity": severity,
            "estimated_financial_impact": impact_est,
        },
        "main_opportunity": {
            "title": "Optimiser la trésorerie" if risk_label == "LOW" else "Accélérer les encaissements",
            "description": opportunity_description,
            "potential_benefit": primary_rec.get("expected_impact", "Amélioration de la marge de manœuvre."),
        },
        "cash_position_analysis": (
            f"Solde {_format_mad(treasury_balance)}, point bas 30j {_format_mad(forecast_min_balance)}, "
            f"autonomie estimée {runway_months} mois. {runway.get('interpretation', '')}"
        ),
        "outlook_30_days": (
            f"Sur 30 jours : surveiller encaissements, dépenses critiques et solde minimum attendu "
            f"({_format_mad(forecast_min_balance)}). Niveau de risque {risk_label}."
        ),
        "recommended_decision": {
            "action": decision_title,
            "rationale": decision_why,
            "expected_outcome": decision_impact,
            "urgency": "Immédiate" if risk_label in {"CRITICAL", "HIGH"} else "Moyenne",
        },
        "immediate_actions": [
            {
                "action": decision_title,
                "why": decision_why,
                "deadline": "Cette semaine" if risk_label in {"CRITICAL", "HIGH"} else decision_horizon,
            }
        ],
        "situation_financiere": "",
        "forces_observees": strengths[:5],
        "points_de_vigilance": vigilance[:7],
        "analyse_risque": {
            "global_risk_level": risk_label,
            "global_risk_score": risk_score,
            "main_risk": {
                "description": main_risk_description,
                "probability": (
                    "Faible" if risk_label == "LOW" else "Moyenne"
                ),
                "business_impact": main_risk.get("impact", ""),
                "urgency": main_risk.get("urgency", "Dans 30 jours"),
            },
        },
        "opportunite_majeure": {
            "description": opportunity_description,
            "benefit": primary_rec.get("expected_impact", ""),
            "difficulty": primary_rec.get("difficulty", "Medium"),
        },
        "decision_prioritaire": {
            "titre": decision_title,
            "pourquoi": decision_why,
            "impact_attendu": decision_impact,
            "horizon_temporel": decision_horizon,
        },
        "actions_prioritaires": [
            {"action": decision_title, "impact_attendu": decision_impact, "pourquoi": decision_why}
        ],
        "perspectives_30_jours": "",
        "risques_court_terme": risk_label,
        "risques_court_terme_description": main_risk_description,
    }
    analysis["situation_financiere"] = analysis["financial_situation"]
    analysis["perspectives_30_jours"] = analysis["outlook_30_days"]
    return analysis


def _normalize_analysis(payload: dict, context: dict, locale: str = DEFAULT_LOCALE) -> dict:
    """Guarantee V3 executive schema with legacy aliases."""

    fallback = normalize_executive_analysis(_rule_based_fallback(context), locale)
    if not isinstance(payload, dict):
        return fallback

    normalized = {**fallback, **payload}
    normalized["executive_summary"] = (
        payload.get("executive_summary")
        or payload.get("executive_briefing")
        or fallback["executive_summary"]
    )
    normalized["executive_briefing"] = normalized["executive_summary"]
    normalized["financial_situation"] = (
        payload.get("financial_situation")
        or payload.get("situation_financiere")
        or fallback["financial_situation"]
    )
    normalized["outlook_30_days"] = (
        payload.get("outlook_30_days")
        or payload.get("perspectives_30_jours")
        or fallback["outlook_30_days"]
    )
    normalized["cash_position_analysis"] = (
        payload.get("cash_position_analysis") or fallback["cash_position_analysis"]
    )

    main_risk = payload.get("main_risk") if isinstance(payload.get("main_risk"), dict) else {}
    if not main_risk and isinstance(payload.get("analyse_risque"), dict):
        ar = payload["analyse_risque"]
        mr = ar.get("main_risk") if isinstance(ar.get("main_risk"), dict) else {}
        main_risk = {
            "title": "Risque principal",
            "description": mr.get("description", ""),
            "severity": ar.get("global_risk_level", "Medium"),
            "estimated_financial_impact": mr.get("business_impact", ""),
        }
    normalized["main_risk"] = {**fallback["main_risk"], **main_risk}

    main_opp = payload.get("main_opportunity") if isinstance(payload.get("main_opportunity"), dict) else {}
    if not main_opp and isinstance(payload.get("opportunite_majeure"), dict):
        om = payload["opportunite_majeure"]
        main_opp = {
            "title": "Opportunité",
            "description": om.get("description", ""),
            "potential_benefit": om.get("benefit", ""),
        }
    normalized["main_opportunity"] = {**fallback["main_opportunity"], **main_opp}

    rec_dec = payload.get("recommended_decision") if isinstance(payload.get("recommended_decision"), dict) else {}
    if not rec_dec and isinstance(payload.get("decision_prioritaire"), dict):
        dp = payload["decision_prioritaire"]
        rec_dec = {
            "action": dp.get("titre", ""),
            "rationale": dp.get("pourquoi", ""),
            "expected_outcome": dp.get("impact_attendu", ""),
            "urgency": "Medium",
        }
    normalized["recommended_decision"] = {**fallback["recommended_decision"], **rec_dec}

    actions = payload.get("immediate_actions") or []
    if not actions and payload.get("actions_prioritaires"):
        actions = [
            {
                "action": a.get("action", ""),
                "why": a.get("pourquoi", ""),
                "deadline": "30 jours",
            }
            for a in payload["actions_prioritaires"]
        ]
    normalized["immediate_actions"] = actions or fallback["immediate_actions"]

    normalized["forces_observees"] = payload.get("forces_observees") or fallback.get("forces_observees", [])
    normalized["points_de_vigilance"] = payload.get("points_de_vigilance") or fallback.get("points_de_vigilance", [])
    normalized["situation_financiere"] = normalized["financial_situation"]
    normalized["perspectives_30_jours"] = normalized["outlook_30_days"]
    return normalized


def generate_executive_analysis(context: dict, locale: str = DEFAULT_LOCALE) -> dict:
    """Generate executive-grade treasury analysis."""

    locale = normalize_locale(locale)
    system_prompt = SYSTEM_PROMPTS.get(locale, SYSTEM_PROMPTS["fr"])

    try:
        resp = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        context,
                        ensure_ascii=False,
                        default=_json_serializer,
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1800,
        )

        if not getattr(resp, "choices", None):
            logger.warning("LLM returned no choices; using fallback")
            return normalize_executive_analysis(_rule_based_fallback(context), locale)

        sanitized = _sanitize_llm_response(resp.choices[0].message.content or "")
        try:
            return normalize_executive_analysis(
                _normalize_analysis(json.loads(sanitized), context, locale), locale
            )
        except Exception as exc:
            logger.warning("Executive LLM JSON parsing failed: %s; fallback activated", exc)
            return normalize_executive_analysis(_rule_based_fallback(context), locale)

    except Exception as exc:
        logger.exception("Executive LLM call failed: %s", exc)
        return normalize_executive_analysis(_rule_based_fallback(context), locale)


def generate_llm_narrative(context: dict) -> dict:
    """Backward-compatible narrative function for older call sites."""

    try:
        narrative_gen = FinancialNarrativeGenerator()
        return narrative_gen.generate_full_narrative(
            current_balance=context.get("treasury_balance", 0),
            net_cashflow=context.get("avg_daily_cashflow", 0),
            liquidity_stress=0.0,
            risk_level=context.get("risk_level", "low"),
            min_balance_30d=0.0,
            balance_decline_rate=0.0,
            trend=context.get("forecast_trend", "stable"),
            volatility=0.0,
            confidence_score=0.9,
            predicted_negative_day=context.get("days_until_zero"),
            recommendations=[],
        )
    except Exception as exc:
        logger.warning("Compatibility generate_llm_narrative failed: %s", exc)
        return {}
