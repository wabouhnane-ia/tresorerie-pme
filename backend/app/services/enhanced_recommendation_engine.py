"""
Digital CFO recommendation and risk engine.

This module stays downstream of the frozen forecasting and memory layers. It
turns treasury facts into business decisions without exposing model terminology.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.core.locale import DEFAULT_LOCALE, normalize_locale
from app.i18n.recommendation_translations import localize_recommendation_item, localize_risk_dict


@dataclass
class ForecastMetrics:
    """Business-facing metrics extracted from forecast data."""

    min_balance_30d: float
    min_balance_day: int
    balance_decline_rate: float
    predicted_negative_day: Optional[int]
    volatility: float
    confidence_score: float
    trend: str


@dataclass
class RecommendationItem:
    """SMART recommendation output used by API, storage, and UI."""

    title: str
    why: str
    expected_impact: str
    difficulty: str
    priority: str
    time_horizon: str
    category: str
    description: str
    severity: str
    recommended_action: str
    confidence_score: float
    business_impact: str
    rule_based: bool = True
    forecast_driven: bool = False
    llm_enhanced: bool = False
    i18n_context: dict[str, Any] = field(default_factory=dict)

    @property
    def reasoning(self) -> str:
        return self.why


class EnhancedRecommendationEngine:
    """Rule-based Digital CFO layer for recommendations and risk intelligence."""

    PRIORITY_ORDER = {
        "Critique": 0,
        "Critical": 0,
        "Élevée": 1,
        "High": 1,
        "Moyenne": 2,
        "Medium": 2,
        "Faible": 3,
        "Low": 3,
    }
    SEVERITY_ORDER = {
        "critique": 0,
        "critical": 0,
        "élevée": 1,
        "élevé": 1,
        "high": 1,
        "moyenne": 2,
        "medium": 2,
        "faible": 3,
        "low": 3,
    }

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self.locale = normalize_locale(locale)
        self.recommendations: list[RecommendationItem] = []

    def analyze_forecast_metrics(
        self,
        forecast_data: list[dict],
        current_balance: float,
    ) -> ForecastMetrics:
        if not forecast_data:
            return ForecastMetrics(
                min_balance_30d=current_balance,
                min_balance_day=0,
                balance_decline_rate=0.0,
                predicted_negative_day=None,
                volatility=0.0,
                confidence_score=0.0,
                trend="unknown",
            )

        import statistics

        # yhat from Prophet/LSTM is already the absolute treasury balance at each date, not a delta
        balances_30d = [current_balance]
        negative_day = None

        for i, point in enumerate(forecast_data[:30]):
            # yhat is the absolute forecasted balance, not a change
            forecasted_balance = float(point.get("yhat") or 0)
            balances_30d.append(forecasted_balance)
            if forecasted_balance < 0 and negative_day is None:
                negative_day = i + 1

        # Calculate daily changes for volatility (difference between consecutive forecasted balances)
        daily_changes = []
        for i in range(1, len(balances_30d)):
            daily_changes.append(balances_30d[i] - balances_30d[i-1])

        min_balance = min(balances_30d)
        min_balance_day = balances_30d.index(min_balance)
        decline_rate = (balances_30d[-1] - balances_30d[0]) / max(len(balances_30d) - 1, 1)
        volatility = statistics.stdev(daily_changes) if len(daily_changes) > 1 else 0.0

        if decline_rate < -5000:
            trend = "declining"
        elif decline_rate > 5000:
            trend = "improving"
        else:
            trend = "stable"

        mid_point = min(14, len(forecast_data) - 1)
        yhat = float(forecast_data[mid_point].get("yhat") or 0)
        lower = float(forecast_data[mid_point].get("yhat_lower") or yhat)
        upper = float(forecast_data[mid_point].get("yhat_upper") or yhat)
        denominator = max(abs(yhat) * 2, 100000)
        confidence = 1.0 - (abs(upper - lower) / denominator)
        confidence = max(0.0, min(1.0, confidence))

        return ForecastMetrics(
            min_balance_30d=min_balance,
            min_balance_day=min_balance_day,
            balance_decline_rate=decline_rate,
            predicted_negative_day=negative_day,
            volatility=volatility,
            confidence_score=confidence,
            trend=trend,
        )

    def generate_recommendations(
        self,
        current_balance: float,
        net_cashflow: float,
        liquidity_stress: float,
        risk_level: str,
        forecast_metrics: ForecastMetrics,
    ) -> list[RecommendationItem]:
        self.recommendations = []
        risk_level = (risk_level or "low").lower()

        if forecast_metrics.predicted_negative_day and forecast_metrics.predicted_negative_day <= 7:
            self._add_emergency_liquidity(forecast_metrics)
        elif forecast_metrics.predicted_negative_day and forecast_metrics.predicted_negative_day <= 30:
            self._add_preventive_liquidity(forecast_metrics)

        if risk_level in {"high", "critical"} or liquidity_stress >= 0.8:
            self._add_cash_preservation(current_balance, net_cashflow, forecast_metrics)
        elif risk_level == "medium" or liquidity_stress >= 0.5:
            self._add_working_capital(current_balance, net_cashflow, forecast_metrics)

        if net_cashflow < 0:
            self._add_cost_control(net_cashflow, forecast_metrics)

        if forecast_metrics.volatility > max(abs(net_cashflow) * 2, 20000):
            self._add_volatility_control(forecast_metrics)

        if forecast_metrics.trend == "declining":
            self._add_revenue_protection(forecast_metrics)

        if risk_level == "low" and current_balance > 0 and net_cashflow >= 0:
            self._add_cash_optimization(current_balance, net_cashflow, forecast_metrics)

        if not self.recommendations:
            self._add_monitoring(current_balance, net_cashflow)

        self.recommendations = self._deduplicate(self.recommendations)
        self.recommendations.sort(
            key=lambda rec: (
                self.PRIORITY_ORDER.get(rec.priority, 9),
                self.SEVERITY_ORDER.get(rec.severity, 9),
                -rec.confidence_score,
            )
        )
        if self.locale != "fr":
            localized: list[RecommendationItem] = []
            fields = set(RecommendationItem.__dataclass_fields__)
            for rec in self.recommendations[:6]:
                item = localize_recommendation_item(self._recommendation_to_dict(rec), self.locale)
                payload = {k: v for k, v in item.items() if k in fields}
                localized.append(RecommendationItem(**payload))
            return localized
        return self.recommendations[:6]

    def generate_risk_intelligence(
        self,
        current_balance: float,
        net_cashflow: float,
        liquidity_stress: float,
        risk_level: str,
        forecast_metrics: ForecastMetrics,
    ) -> dict:
        risks = [
            self._liquidity_risk(current_balance, net_cashflow, liquidity_stress, forecast_metrics),
            self._cashflow_risk(net_cashflow, forecast_metrics),
            self._revenue_risk(net_cashflow, forecast_metrics),
            self._expense_inflation_risk(net_cashflow, forecast_metrics),
            self._volatility_risk(net_cashflow, forecast_metrics),
            self._forecast_deterioration_risk(forecast_metrics),
        ]
        top_risks = sorted(risks, key=lambda risk: risk["severity_score"], reverse=True)[:3]
        global_score = max([risk["severity_score"] for risk in top_risks] + [0])
        mapped_level = self._risk_level_from_score(global_score)
        existing_level = (risk_level or "").lower()
        if existing_level == "critical":
            mapped_level = "CRITICAL"
            global_score = max(global_score, 80)
        elif existing_level == "high":
            global_score = max(global_score, 65)
            mapped_level = self._risk_level_from_score(global_score)

        risks_out = [
            {key: value for key, value in risk.items() if key != "severity_score"}
            for risk in top_risks
        ]
        if self.locale != "fr":
            risks_out = [localize_risk_dict(r, self.locale) for r in risks_out]
        return {
            "global_risk_level": mapped_level,
            "global_risk_score": int(min(100, max(0, global_score))),
            "top_risks": risks_out,
        }

    def to_dict(self) -> list[dict]:
        return [self._recommendation_to_dict(rec) for rec in self.recommendations]

    @staticmethod
    def _recommendation_to_dict(rec: RecommendationItem) -> dict:
        data = asdict(rec)
        data["reasoning"] = rec.reasoning
        return data

    @staticmethod
    def _format_mad(value: float) -> str:
        return f"{value:,.0f} MAD"

    def _add(self, **kwargs):
        i18n_context = kwargs.pop("i18n_context", {})
        self.recommendations.append(RecommendationItem(i18n_context=i18n_context, **kwargs))

    def _add_emergency_liquidity(self, metrics: ForecastMetrics):
        day = metrics.predicted_negative_day or 7
        shortfall = max(0, abs(metrics.min_balance_30d))
        self._add(
            title="Sécuriser la couverture de trésorerie immédiate",
            why=f"La trésorerie est projetée négative dans {day} jours, avec un point bas potentiel de {self._format_mad(metrics.min_balance_30d)}.",
            expected_impact=f"Couvrir le déficit projeté d'environ {self._format_mad(shortfall)} et protéger la paie, les fournisseurs et les opérations.",
            difficulty="Moyen",
            priority="Critique",
            time_horizon="0-7 jours",
            category="Liquidité",
            description="Confirmer la disponibilité des lignes de crédit, accélérer les encaissements majeurs et geler les paiements non essentiels jusqu'à couverture du besoin.",
            severity="critical",
            recommended_action="Activer un plan de protection de trésorerie de 7 jours avec revue quotidienne.",
            confidence_score=max(metrics.confidence_score, 0.8),
            business_impact="Éviter une interruption opérationnelle liée au manque de liquidités.",
            forecast_driven=True,
            i18n_context={
                "day": day,
                "min_balance": self._format_mad(metrics.min_balance_30d),
                "shortfall": self._format_mad(shortfall),
            },
        )

    def _add_preventive_liquidity(self, metrics: ForecastMetrics):
        day = metrics.predicted_negative_day or 30
        self._add(
            title="Préparer un renforcement de liquidité avant tension",
            why=f"La trésorerie peut devenir négative dans environ {day} jours si la trajectoire se poursuit.",
            expected_impact="Préserver la continuité opérationnelle sur 30 jours et éviter un financement de dernière minute.",
            difficulty="Moyen",
            priority="Élevée",
            time_horizon="7-30 jours",
            category="Liquidité",
            description="Préparer un plan de financement de secours et prioriser les encaissements avant que la tension projetée ne se matérialise.",
            severity="high",
            recommended_action="Constituer un pont de trésorerie 30 jours via accélération des encaissements, ajustement des délais fournisseurs et lignes de crédit disponibles.",
            confidence_score=max(metrics.confidence_score, 0.75),
            business_impact="Réduire le risque de liquidité à court terme avant qu'il n'escalade.",
            forecast_driven=True,
        )

    def _add_cash_preservation(self, balance: float, net_cashflow: float, metrics: ForecastMetrics):
        self._add(
            title="Préserver les réserves de trésorerie immédiatement",
            why=f"La trésorerie actuelle est de {self._format_mad(balance)} et la génération nette récente est de {self._format_mad(net_cashflow)} par jour.",
            expected_impact="Allonger la piste financière et conserver la marge pour payer les fournisseurs stratégiques.",
            difficulty="Facile",
            priority="Élevée",
            time_horizon="0-15 jours",
            category="Liquidité",
            description="Suspendre les dépenses discrétionnaires, valider les paiements importants et conserver suffisamment de cash pour les engagements critiques.",
            severity="high",
            recommended_action="Mettre en place des seuils d'approbation temporaires pour les sorties non essentielles.",
            confidence_score=0.9,
            business_impact="Protéger la flexibilité opérationnelle immédiate.",
            rule_based=True,
            forecast_driven=metrics.trend == "declining",
        )

    def _add_working_capital(self, balance: float, net_cashflow: float, metrics: ForecastMetrics):
        self._add(
            title="Améliorer la discipline du fonds de roulement",
            why=f"La réserve actuelle est de {self._format_mad(balance)} tandis que le flux net journalier récent est de {self._format_mad(net_cashflow)}.",
            expected_impact="Améliorer la disponibilité de cash sur 30 jours sans modifier le modèle d'affaires.",
            difficulty="Moyen",
            priority="Moyenne",
            time_horizon="15-30 jours",
            category="Fonds de roulement",
            description="Raccourcir les délais de recouvrement clients et aligner les paiements fournisseurs sur les encaissements.",
            severity="medium",
            recommended_action="Revoir les principales créances en retard et négocier l'échéancier avec les fournisseurs stratégiques.",
            confidence_score=0.82,
            business_impact="Renforcer le cycle de conversion du cash.",
            rule_based=True,
            forecast_driven=metrics.trend != "unknown",
        )

    def _add_cost_control(self, net_cashflow: float, metrics: ForecastMetrics):
        self._add(
            title="Réduire les dépenses discrétionnaires",
            why=f"Le flux net récent est négatif à {self._format_mad(net_cashflow)} par jour, ce qui érode progressivement la trésorerie.",
            expected_impact="Freiner l'érosion de trésorerie et libérer du cash pour les opérations essentielles.",
            difficulty="Facile",
            priority="Élevée" if metrics.trend == "declining" else "Moyenne",
            time_horizon="0-30 jours",
            category="Maîtrise des coûts",
            description="Identifier les dépenses non critiques pouvant être retardées, renégociées ou annulées ce mois-ci.",
            severity="high" if metrics.trend == "declining" else "medium",
            recommended_action="Lancer une revue des dépenses sur 30 jours centrée sur les coûts variables et discrétionnaires.",
            confidence_score=0.88,
            business_impact="Réduire la fuite de cash quotidienne.",
            rule_based=True,
        )

    def _add_volatility_control(self, metrics: ForecastMetrics):
        self._add(
            title="Stabiliser la visibilité des flux de trésorerie",
            why=f"Les mouvements de trésorerie journaliers sont volatils, avec des variations autour de {self._format_mad(metrics.volatility)}.",
            expected_impact="Donner à la direction un avertissement plus précoce sur les déficits ou excédents de cash.",
            difficulty="Facile",
            priority="Moyenne",
            time_horizon="Prochains 30 jours",
            category="Optimisation de trésorerie",
            description="Passer d'une revue mensuelle à une planification hebdomadaire du cash et isoler les principaux moteurs de mouvement.",
            severity="medium",
            recommended_action="Mettre en place une vue roulante sur 13 semaines mise à jour chaque semaine.",
            confidence_score=max(metrics.confidence_score, 0.7),
            business_impact="Améliorer la prévisibilité pour les décisions de gestion.",
            forecast_driven=True,
        )

    def _add_revenue_protection(self, metrics: ForecastMetrics):
        self._add(
            title="Protéger les encaissements",
            why=f"La trajectoire de trésorerie décline d'environ {self._format_mad(abs(metrics.balance_decline_rate))} par jour.",
            expected_impact="Stabiliser les encaissements et réduire la dépendance au financement.",
            difficulty="Moyen",
            priority="Élevée",
            time_horizon="15-30 jours",
            category="Protection des encaissements",
            description="Prioriser les encaissements confirmés, résoudre les factures bloquées et éviter les pertes de revenus lors du prochain cycle.",
            severity="high",
            recommended_action="Organiser un sprint de relance des principaux clients avec un propriétaire et un objectif hebdomadaire.",
            confidence_score=max(metrics.confidence_score, 0.75),
            business_impact="Stopper la détérioration du cash disponible.",
            forecast_driven=True,
        )

    def _add_cash_optimization(self, balance: float, net_cashflow: float, metrics: ForecastMetrics):
        self._add(
            title="Optimiser l'allocation des excédents de trésorerie",
            why=f"La trésorerie est positive à {self._format_mad(balance)} et la génération de cash récente est positive à {self._format_mad(net_cashflow)} par jour.",
            expected_impact="Améliorer le rendement de la trésorerie tout en préservant la liquidité opérationnelle.",
            difficulty="Moyen",
            priority="Moyenne",
            time_horizon="30-90 jours",
            category="Optimisation de trésorerie",
            description="Séparer la trésorerie opérationnelle de l'excédent et définir ce qui peut être investi, réservé ou utilisé pour réduire la dette.",
            severity="low",
            recommended_action="Définir une réserve minimale de trésorerie opérationnelle et n'allouer que le surplus au-delà de cette réserve.",
            confidence_score=max(metrics.confidence_score, 0.8),
            business_impact="Valoriser le cash inactif sans affaiblir la liquidité.",
            rule_based=True,
        )

    def _add_monitoring(self, balance: float, net_cashflow: float):
        self._add(
            title="Maintenir un pilotage trésorerie hebdomadaire",
            why=f"La trésorerie est de {self._format_mad(balance)} et le flux net récent est de {self._format_mad(net_cashflow)} par jour.",
            expected_impact="Informer la direction et détecter rapidement toute détérioration.",
            difficulty="Facile",
            priority="Faible",
            time_horizon="Prochains 30 jours",
            category="Optimisation de trésorerie",
            description="Maintenir une revue hebdomadaire de la trésorerie, des encaissements, des paiements fournisseurs et des engagements à venir.",
            severity="low",
            recommended_action="Revoir la position de trésorerie chaque semaine avec une liste de surveillance sur 30 jours.",
            confidence_score=0.8,
            business_impact="Préserver le contrôle financier.",
            rule_based=True,
        )

    def _deduplicate(self, recommendations: list[RecommendationItem]) -> list[RecommendationItem]:
        seen = set()
        unique = []
        for rec in recommendations:
            if rec.title in seen:
                continue
            seen.add(rec.title)
            unique.append(rec)
        return unique

    def _risk(self, title, description, probability, impact, urgency, action, score):
        return {
            "title": title,
            "description": description,
            "probability": probability,
            "impact": impact,
            "urgency": urgency,
            "recommended_action": action,
            "severity_score": int(min(100, max(0, score))),
        }

    def _liquidity_risk(self, balance, net_cashflow, stress, metrics):
        if metrics.predicted_negative_day and metrics.predicted_negative_day <= 30:
            score = 90 if metrics.predicted_negative_day <= 7 else 75
            urgency = "Immédiat" if metrics.predicted_negative_day <= 7 else "Sous 30 jours"
            probability = "Élevée"
        elif stress >= 0.8 or balance < abs(net_cashflow) * 15:
            score = 65
            urgency = "Sous 15 jours"
            probability = "Moyenne"
        else:
            score = 25
            urgency = "Suivi mensuel"
            probability = "Faible"
        return self._risk(
            "Risque de liquidité",
            "Risque que la trésorerie disponible ne suffise pas aux engagements opérationnels à court terme.",
            probability,
            "Retards de paiement, pression fournisseurs ou besoin de financement d'urgence.",
            urgency,
            "Protéger la réserve minimale de cash et préparer les leviers d'encaissement ou de financement.",
            score,
        )

    def _cashflow_risk(self, net_cashflow, metrics):
        score = 70 if net_cashflow < 0 and metrics.trend == "declining" else 50 if net_cashflow < 0 else 20
        return self._risk(
            "Risque de flux de trésorerie",
            "Risque que l'exploitation consomme plus de cash qu'elle n'en génère au quotidien.",
            "Élevée" if score >= 70 else "Moyenne" if score >= 50 else "Faible",
            "Érosion de trésorerie et moindre flexibilité de gestion.",
            "Sous 30 jours" if score >= 50 else "Suivi mensuel",
            "Accélérer les encaissements et réduire les sorties non essentielles.",
            score,
        )

    def _revenue_risk(self, net_cashflow, metrics):
        score = 60 if metrics.trend == "declining" else 35 if net_cashflow < 0 else 20
        return self._risk(
            "Risque sur les encaissements",
            "Risque que les entrées de cash ne suivent pas le rythme actuel des dépenses.",
            "Moyenne" if score >= 50 else "Faible",
            "Baisse de génération de cash et tension sur le fonds de roulement.",
            "Sous 30 jours" if score >= 50 else "Suivi mensuel",
            "Prioriser les encaissements confirmés et suivre les principaux clients.",
            score,
        )

    def _expense_inflation_risk(self, net_cashflow, metrics):
        score = 65 if net_cashflow < 0 and metrics.balance_decline_rate < -5000 else 35
        return self._risk(
            "Risque d'inflation des dépenses",
            "Risque que les charges d'exploitation progressent plus vite que la trésorerie générée.",
            "Moyenne" if score >= 50 else "Faible",
            "Compression de marge et consommation de cash évitable.",
            "Sous 30 jours" if score >= 50 else "Suivi mensuel",
            "Revoir les dépenses discrétionnaires et renégocier les postes variables.",
            score,
        )

    def _volatility_risk(self, net_cashflow, metrics):
        threshold = max(abs(net_cashflow) * 2, 20000)
        score = 65 if metrics.volatility > threshold else 25
        return self._risk(
            "Risque de volatilité",
            "Risque que les mouvements de trésorerie soient trop irréguliers pour une planification fiable.",
            "Moyenne" if score >= 50 else "Faible",
            "Trous de trésorerie imprévus ou excédents de cash mal exploités.",
            "Sous 30 jours" if score >= 50 else "Suivi mensuel",
            "Mettre en place un plan de trésorerie glissant hebdomadaire et suivre les principaux flux.",
            score,
        )

    def _forecast_deterioration_risk(self, metrics):
        score = 70 if metrics.trend == "declining" else 25
        return self._risk(
            "Risque de dégradation des perspectives",
            "Risque que la trajectoire de trésorerie à court terme continue de se dégrader.",
            "Élevée" if score >= 70 else "Faible",
            "Moins de temps pour réagir et pression accrue sur le financement.",
            "Sous 30 jours" if score >= 50 else "Suivi mensuel",
            "Déclencher une revue de direction si le solde minimum à 30 jours se dégrade.",
            score,
        )

    @staticmethod
    def _risk_level_from_score(score: int) -> str:
        if score >= 80:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 35:
            return "MEDIUM"
        return "LOW"
