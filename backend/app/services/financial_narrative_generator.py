"""
Financial Narrative Generator
Creates executive-level financial summaries and insights from forecast data and recommendations.
"""

from openai import OpenAI
from app.core.config import settings


client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


class FinancialNarrativeGenerator:
    """
    Generates professional financial narratives from data.
    - Executive summaries
    - Treasury insights
    - Financial reasoning
    - Operational recommendations
    """

    def __init__(self):
        self.model = "meta-llama/llama-3.1-8b-instruct"

    def generate_executive_summary(
        self,
        current_balance: float,
        net_cashflow: float,
        liquidity_stress: float,
        risk_level: str,
        min_balance_30d: float,
        balance_decline_rate: float,
        trend: str,
        scenario: str | None = None,
    ) -> str:
        """Generate 2-3 sentence executive summary of treasury situation."""

        prompt = f"""Tu es analyste trésorerie pour PME marocaines.
Rédige un résumé exécutif de 2-3 phrases sur la situation de trésorerie.
Ton professionnel orienté dirigeant. N'évoque pas l'IA ni les modèles. Réponds en français.

Faits :
- Solde actuel : {current_balance:,.0f} MAD
- Flux net journalier : {net_cashflow:,.0f} MAD
- Indice de tension liquidité : {liquidity_stress:.1%}
- Solde minimum 30 jours : {min_balance_30d:,.0f} MAD
- Taux de baisse journalier : {balance_decline_rate:,.0f} MAD
- Tendance : {trend}
- Niveau de risque : {risk_level}
- Scénario : {scenario}

Contraintes : 2-3 phrases, pas de puces, pas de chiffres dans le texte (qualificatifs : solide, fragile, en baisse).

Rédige le résumé :"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es expert trésorerie pour PME. Tu réponds uniquement en français professionnel.",
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temp for consistency
            max_tokens=150,
        )

        return response.choices[0].message.content.strip()

    def generate_financial_outlook(
        self,
        current_balance: float,
        predicted_negative_day: int | None,
        min_balance_30d: float,
        balance_decline_rate: float,
        volatility: float,
        confidence_score: float,
        net_cashflow: float,
    ) -> str:
        """Generate detailed financial outlook narrative."""

        # Build context string
        if predicted_negative_day:
            outlook_context = (
                f"Tension de liquidité possible dans environ {predicted_negative_day} jours"
            )
        else:
            outlook_context = f"Solde minimum projeté sur 30 jours : {min_balance_30d:,.0f} MAD"

        prompt = f"""Tu es analyste trésorerie. Rédige une perspective financière concise (3-4 phrases) en français.

Contexte :
- Flux net journalier : {net_cashflow:,.0f} MAD
- Baisse journalière : {balance_decline_rate:,.0f} MAD
- Volatilité : {volatility:,.0f} MAD
- Confiance prévision : {confidence_score:.0%}
- {outlook_context}

Contraintes : ton direction, impact métier, pas de jargon technique, pas de puces.

Rédige la perspective :"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es expert trésorerie pour PME. Tu réponds uniquement en français professionnel.",
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )

        return response.choices[0].message.content.strip()

    def generate_risk_analysis(
        self,
        risk_level: str,
        liquidity_stress: float,
        predicted_negative_day: int | None,
        key_triggers: list[str],
    ) -> str:
        """Generate risk analysis narrative."""

        triggers_text = "\n".join([f"- {t}" for t in key_triggers]) if key_triggers else "- Déséquilibre opérationnel global"

        crisis = (
            f"Oui, sous {predicted_negative_day} jours"
            if predicted_negative_day
            else "Pas de crise immédiate"
        )

        prompt = f"""Tu es analyste risque financier. Rédige une évaluation des risques (2-3 phrases) en français.

Profil :
- Niveau de risque : {risk_level}
- Tension liquidité : {liquidity_stress:.0%}
- Déclencheur : {crisis}

Facteurs :
{triggers_text}

Contraintes : impact métier, ton direct, conséquences si inaction.

Rédige l'analyse :"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es expert risque financier pour PME. Tu réponds uniquement en français.",
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=150,
        )

        return response.choices[0].message.content.strip()

    def generate_action_recommendations(
        self,
        recommendations: list[dict],
        risk_level: str,
    ) -> str:
        """Generate executive action plan from structured recommendations."""

        # Extract top 3-4 recommendations
        top_recs = [r for r in recommendations if r.get("severity") in ["critical", "high"]][:4]
        if not top_recs:
            top_recs = recommendations[:3]

        rec_summary = "\n".join([
            f"- {r.get('title')}: {r.get('description', '')}"
            for r in top_recs
        ])

        prompt = f"""Tu es conseiller financier pour PME. Rédige un plan d'action narratif (3-4 phrases) en français.

Niveau de risque : {risk_level}
Recommandations prioritaires :
{rec_summary}

Contraintes : actions de direction, urgence et impact, pas de puces, délais concrets.

Rédige le plan d'action :"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es conseiller financier pour PME. Tu réponds uniquement en français professionnel.",
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )

        return response.choices[0].message.content.strip()

    def generate_full_narrative(
        self,
        current_balance: float,
        net_cashflow: float,
        liquidity_stress: float,
        risk_level: str,
        min_balance_30d: float,
        balance_decline_rate: float,
        trend: str,
        volatility: float,
        confidence_score: float,
        predicted_negative_day: int | None,
        recommendations: list[dict],
    ) -> dict:
        """Generate complete AI financial insights package."""

        try:
            executive_summary = self.generate_executive_summary(
                current_balance,
                net_cashflow,
                liquidity_stress,
                risk_level,
                min_balance_30d,
                balance_decline_rate,
                trend,
            )
        except Exception as e:
            executive_summary = f"Résumé indisponible : {str(e)}"

        try:
            financial_outlook = self.generate_financial_outlook(
                current_balance,
                predicted_negative_day,
                min_balance_30d,
                balance_decline_rate,
                volatility,
                confidence_score,
                net_cashflow,
            )
        except Exception as e:
            financial_outlook = ""

        try:
            risk_analysis = self.generate_risk_analysis(
                risk_level,
                liquidity_stress,
                predicted_negative_day,
                self._extract_key_triggers(risk_level, liquidity_stress, balance_decline_rate),
            )
        except Exception as e:
            risk_analysis = ""

        try:
            action_plan = self.generate_action_recommendations(recommendations, risk_level)
        except Exception as e:
            action_plan = ""

        return {
            "executive_summary": executive_summary,
            "financial_outlook": financial_outlook,
            "risk_analysis": risk_analysis,
            "action_plan": action_plan,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _extract_key_triggers(risk_level: str, liquidity_stress: float, balance_decline_rate: float) -> list[str]:
        """Extract key trigger factors for narrative."""
        triggers = []
        
        if balance_decline_rate < -15000:
            triggers.append("Baisse rapide de trésorerie dépassant 15 000 MAD par jour")
        elif balance_decline_rate < -5000:
            triggers.append("Flux net journalier négatif soutenu")
        
        if liquidity_stress > 0.8:
            triggers.append("Indicateurs de tension de liquidité critiques")
        elif liquidity_stress > 0.5:
            triggers.append("Pression de liquidité élevée")
        
        if risk_level == "high":
            triggers.append("Niveau de risque élevé")
        elif risk_level == "medium":
            triggers.append("Pression financière à moyen terme")
        
        return triggers


from datetime import datetime, timezone
