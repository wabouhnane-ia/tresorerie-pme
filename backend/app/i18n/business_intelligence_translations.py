"""Locale-safe Business Intelligence presentation payloads."""

from __future__ import annotations

from copy import deepcopy

from app.core.locale import DEFAULT_LOCALE, normalize_locale


_TEXT = {
    "fr": {
        "health": {
            "excellent": "Excellente santé financière",
            "healthy": "Bonne santé financière",
            "vigilance": "Vigilance",
            "fragile": "Situation fragile",
            "critical": "Situation critique",
        },
        "resilience": {
            "excellent": "Très forte",
            "healthy": "Forte",
            "vigilance": "Modérée",
            "fragile": "Faible",
            "critical": "Critique",
        },
        "severity": {
            "Critical": "Critique",
            "High": "Élevée",
            "Medium": "Moyenne",
            "Low": "Faible",
        },
        "probability": {"high": "Élevée", "medium": "Moyenne", "low": "Faible"},
        "urgency": {"now": "Immédiat", "30": "Sous 30 jours", "month": "Suivi mensuel"},
        "health_explanation": "Autonomie estimée : {months} mois. Niveau de risque global : {risk_level}.",
        "resilience_interpretation_high": "Capacité élevée à absorber un choc de trésorerie.",
        "resilience_interpretation_mid": "Situation gérable avec un pilotage régulier des flux.",
        "resilience_interpretation_low": "Marge de sécurité limitée : des actions de direction sont à prévoir.",
        "runway": "La trésorerie couvre environ {months} mois d'activité au rythme récent.",
        "summary": "Trésorerie à {balance} — santé {health}/100, résilience {resilience}/100, autonomie estimée {runway_months} mois. Risque principal : {risk_title}. Décision prioritaire : {decision_action}.",
        "financial": "Sur les 30 derniers jours : encaissements {inflows}, dépenses {outflows}, flux net {net}. Évolution de la trésorerie : {trend}.",
        "cash": "Autonomie estimée {months} mois. Résilience : {label} ({score}/100).",
        "outlook": "Sur 30 jours : point bas attendu autour de {min_balance}, tendance {trend}. Niveau de risque global : {risk_level}.",
        "main_risk_title": "Risque de trésorerie",
        "main_risk_desc": "La direction doit maintenir une visibilité rapprochée sur les flux et les engagements critiques.",
        "opportunity_title": "Optimiser la trésorerie",
        "opportunity_desc": "Structurer une réserve minimale et utiliser le surplus sans fragiliser les opérations.",
        "decision_action": "Tenir une revue trésorerie hebdomadaire",
        "decision_rationale": "Le pilotage régulier sécurise la position de trésorerie et accélère la réaction aux tensions.",
        "decision_outcome": "Meilleure visibilité sur les encaissements, les dépenses et les priorités de paiement.",
        "deadline": "Cette semaine",
        "alert_title": "Pilotage régulier recommandé",
        "alert_desc": "Aucun signal critique immédiat ; maintenir la visibilité hebdomadaire.",
        "alert_impact": "Préserver la capacité de réaction de la direction.",
        "alert_action": "Tenir une revue trésorerie hebdomadaire avec les principaux flux entrants et sortants.",

        # Cash Runway
        "cash_runway": {
            "burn_rate_interpretation": "Au rythme actuel de consommation ({avg_net} par jour), la trésorerie couvre environ {months} mois d'activité.",
            "expense_coverage_interpretation": "La trésorerie actuelle ({balance}) couvre environ {months} mois de dépenses au rythme des 30 derniers jours (encaissements récents : {monthly_inflows}).",
            "stable_buffer_interpretation": "Trésorerie disponible de {balance} sans sorties significatives enregistrées sur la période récente.",
            "insufficient_data_interpretation": "Données insuffisantes pour estimer l'autonomie de trésorerie.",
            "declining_trend_adjustment": " Ajustement prudent : la trésorerie recule sur la période observée.",
            "forecast_decline_adjustment": " La trajectoire récente suggère une marge de sécurité à resserrer.",
        },

        # Financial Health Drivers
        "health_drivers": {
            "runway": "Autonomie estimée : {months} mois.",
            "positive_cashflow": "Flux net récent positif.",
            "negative_cashflow": "Flux net récent négatif : {cashflow} par jour.",
            "risk_level": "Niveau de risque global : {risk_level}.",
        },

        # Resilience Drivers
        "resilience_drivers": {
            "runway": "Horizon de trésorerie estimé : {months} mois.",
            "positive_cashflow": "Les encaissements couvrent le rythme de dépenses récent.",
            "negative_cashflow": "Consommation nette de {cashflow} par jour.",
            "improving_trend": "La trésorerie progresse sur la période observée.",
            "declining_trend": "La trésorerie recule : vigilance sur la marge de sécurité.",
            "outflow_spike": "Dépenses en hausse de {pct}% sur 30 jours.",
            "inflow_drop": "Encaissements en baisse de {pct}% sur 30 jours.",
        },

        # Alerts
        "alerts": {
            "critical_liquidity_title": "Liquidité critique à traiter aujourd'hui",
            "critical_liquidity_desc": "Autonomie estimée à {days} jours seulement ({interpretation})",
            "critical_liquidity_impact": "Risque de retard de paiement sur environ {amount}.",
            "critical_liquidity_action": "Bloquer les sorties non essentielles, activer les relances clients et sécuriser une ligne de trésorerie.",
            "short_margin_title": "Marge de trésorerie courte",
            "short_margin_impact": "Peu de capacité à absorber un retard client ou une dépense imprévue.",
            "short_margin_action": "Établir un plan de trésorerie sur 30 jours avec priorités de paiement.",
            "deterioration_title": "La trésorerie se dégrade",
            "deterioration_desc": "Consommation nette moyenne de {avg_net} par jour sur 30 jours.",
            "deterioration_impact": "Érosion estimée d'environ {monthly_drain} par mois si rien ne change.",
            "deterioration_action": "Réduire les charges variables et accélérer les encaissements confirmés.",
            "spending_spike_title": "Hausse anormale des dépenses",
            "spending_spike_desc": "Les sorties ont augmenté de {pct}% vs la période précédente.",
            "spending_spike_impact": "Surcoût estimé d'environ {amount} sur 30 jours.",
            "spending_spike_action": "Valider chaque paiement supérieur au seuil habituel et reporter les dépenses non critiques.",
            "spending_accel_title": "Dépenses en accélération",
            "spending_accel_desc": "Sorties en hausse de {pct}% sur 30 jours.",
            "spending_accel_impact": "Pression sur la marge de trésorerie disponible.",
            "spending_accel_action": "Revoir les postes variables et les échéances fournisseurs.",
            "inflow_drop_title": "Encaissements en forte baisse",
            "inflow_drop_desc": "Encaissements récents en recul de {pct}% — dépendance accrue à quelques entrées de cash.",
            "inflow_drop_impact": "Manque à gagner de trésorerie d'environ {amount} vs le mois précédent.",
            "inflow_drop_action": "Identifier les clients ou contrats en retard et sécuriser les factures à forte valeur.",
            "inflow_slow_title": "Ralentissement des encaissements",
            "inflow_slow_desc": "Encaissements en baisse de {pct}% sur 30 jours.",
            "inflow_slow_impact": "Risque de tension sur le cycle de trésorerie.",
            "inflow_slow_action": "Relancer les créances ouvertes et confirmer les dates de paiement clients.",
            "forecast_low_title": "Point bas de trésorerie à venir",
            "forecast_low_desc": "Le niveau de trésorerie pourrait descendre vers {min_balance}.",
            "forecast_low_impact": "Écart potentiel d'environ {amount} par rapport au solde actuel.",
            "forecast_low_action": "Planifier les encaissements et reports de paiement avant la semaine de tension.",
            "opportunity_title": "Opportunité : optimiser l'excédent de trésorerie",
            "opportunity_desc": "Trésorerie de {balance} avec génération de cash positive.",
            "opportunity_impact": "Améliorer le rendement du cash excédentaire sans fragiliser les opérations.",
            "opportunity_action": "Définir une réserve opérationnelle minimale et allouer le surplus (remboursement dette, placement court terme).",
        },

        # Risks
        "risks": {
            "default_title": "Risque de trésorerie",
            "high_probability": "Élevée",
            "medium_probability": "Moyenne",
            "immediate_urgency": "Immédiat",
        },

        # Decisions
        "decisions": {
            "default_action": "Instaurer une revue trésorerie hebdomadaire",
            "default_benefit": "Détecter plus tôt les tensions et prioriser les encaissements.",
            "default_justification": "Autonomie estimée à {months} mois — le pilotage régulier sécurise cette position.",
            "default_horizon": "Prochains 30 jours",
        },

        # Briefing
        "briefing": {
            "surplus_opportunity_title": "Renforcer la valeur de l'excédent de trésorerie",
            "surplus_opportunity_desc": "Avec {balance} en caisse et des encaissements qui couvrent le rythme de dépenses, la direction peut structurer une réserve minimale et utiliser le surplus.",
            "surplus_opportunity_benefit": "Améliorer le rendement du cash sans fragiliser les opérations.",
            "deficit_opportunity_title": "Accélérer les encaissements confirmés",
            "deficit_opportunity_desc": "Prioriser les relances sur les créances ouvertes pour compenser la consommation de {avg_net} par jour.",
            "deficit_opportunity_benefit": "Réduire la pression sur la trésorerie dans les 30 prochains jours.",
            "default_decision_action": "Piloter la trésorerie en comité de direction",
            "default_decision_horizon": "30 jours",
        },
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
        "summary": "Treasury balance {balance} — health {health}/100, resilience {resilience}/100, estimated runway {runway_months} months. Main risk: {risk_title}. Priority decision: {decision_action}.",
        "financial": "Over the last 30 days: inflows {inflows}, outflows {outflows}, net flow {net}. Treasury trend: {trend}.",
        "cash": "Estimated runway {months} months. Resilience: {label} ({score}/100).",
        "outlook": "Over 30 days: expected low balance around {min_balance}, trend {trend}. Overall risk level: {risk_level}.",
        "main_risk_title": "Treasury risk",
        "main_risk_desc": "Management should keep close visibility over cash flows and critical commitments.",
        "opportunity_title": "Optimize treasury",
        "opportunity_desc": "Structure a minimum reserve and use surplus cash without weakening operations.",
        "decision_action": "Run a weekly treasury review",
        "decision_rationale": "Regular steering protects the treasury position and speeds up response to pressure.",
        "decision_outcome": "Better visibility over collections, spending and payment priorities.",
        "deadline": "This week",
        "alert_title": "Regular steering recommended",
        "alert_desc": "No immediate critical signal; keep weekly visibility.",
        "alert_impact": "Preserve management's ability to react.",
        "alert_action": "Run a weekly treasury review with the main inflows and outflows.",

        # Cash Runway
        "cash_runway": {
            "burn_rate_interpretation": "At the current burn rate ({avg_net} per day), treasury covers about {months} months of activity.",
            "expense_coverage_interpretation": "Current treasury ({balance}) covers about {months} months of expenses at the last 30 days' pace (recent inflows: {monthly_inflows}).",
            "stable_buffer_interpretation": "Available treasury of {balance} with no significant outflows recorded in the recent period.",
            "insufficient_data_interpretation": "Insufficient data to estimate treasury runway.",
            "declining_trend_adjustment": " Prudent adjustment: treasury is declining over the observed period.",
            "forecast_decline_adjustment": " Recent trajectory suggests tightening the safety margin.",
        },

        # Financial Health Drivers
        "health_drivers": {
            "runway": "Estimated runway: {months} months.",
            "positive_cashflow": "Recent net cash flow positive.",
            "negative_cashflow": "Recent net cash flow negative: {cashflow} per day.",
            "risk_level": "Overall risk level: {risk_level}.",
        },

        # Resilience Drivers
        "resilience_drivers": {
            "runway": "Estimated treasury horizon: {months} months.",
            "positive_cashflow": "Collections cover the recent spending pace.",
            "negative_cashflow": "Net consumption of {cashflow} per day.",
            "improving_trend": "Treasury is improving over the observed period.",
            "declining_trend": "Treasury is declining: vigilance on the safety margin.",
            "outflow_spike": "Expenses up {pct}% over 30 days.",
            "inflow_drop": "Collections down {pct}% over 30 days.",
        },

        # Alerts
        "alerts": {
            "critical_liquidity_title": "Critical liquidity to address today",
            "critical_liquidity_desc": "Estimated runway only {days} days ({interpretation})",
            "critical_liquidity_impact": "Risk of late payments on approximately {amount}.",
            "critical_liquidity_action": "Block non-essential outflows, activate customer follow-ups and secure a credit line.",
            "short_margin_title": "Short treasury margin",
            "short_margin_impact": "Little capacity to absorb a late customer payment or unexpected expense.",
            "short_margin_action": "Establish a 30-day treasury plan with payment priorities.",
            "deterioration_title": "Treasury is deteriorating",
            "deterioration_desc": "Average net consumption of {avg_net} per day over 30 days.",
            "deterioration_impact": "Estimated erosion of approximately {monthly_drain} per month if nothing changes.",
            "deterioration_action": "Reduce variable costs and accelerate confirmed collections.",
            "spending_spike_title": "Abnormal spending increase",
            "spending_spike_desc": "Outflows increased by {pct}% vs the previous period.",
            "spending_spike_impact": "Estimated additional cost of approximately {amount} over 30 days.",
            "spending_spike_action": "Validate each payment above the usual threshold and postpone non-critical expenses.",
            "spending_accel_title": "Accelerating expenses",
            "spending_accel_desc": "Outflows up {pct}% over 30 days.",
            "spending_accel_impact": "Pressure on available treasury margin.",
            "spending_accel_action": "Review variable items and supplier deadlines.",
            "inflow_drop_title": "Sharp decline in collections",
            "inflow_drop_desc": "Recent collections down {pct}% — increased dependence on a few cash inflows.",
            "inflow_drop_impact": "Treasury shortfall of approximately {amount} vs the previous month.",
            "inflow_drop_action": "Identify late customers or contracts and secure high-value invoices.",
            "inflow_slow_title": "Slowing collections",
            "inflow_slow_desc": "Collections down {pct}% over 30 days.",
            "inflow_slow_impact": "Risk of pressure on the treasury cycle.",
            "inflow_slow_action": "Follow up on open receivables and confirm customer payment dates.",
            "forecast_low_title": "Upcoming treasury low point",
            "forecast_low_desc": "Treasury level could drop to around {min_balance}.",
            "forecast_low_impact": "Potential gap of approximately {amount} from current balance.",
            "forecast_low_action": "Plan collections and payment deferrals before the stress week.",
            "opportunity_title": "Opportunity: optimize treasury surplus",
            "opportunity_desc": "Treasury of {balance} with positive cash generation.",
            "opportunity_impact": "Improve surplus cash yield without weakening operations.",
            "opportunity_action": "Define a minimum operating reserve and allocate the surplus (debt repayment, short-term investment).",
        },

        # Risks
        "risks": {
            "default_title": "Treasury risk",
            "high_probability": "High",
            "medium_probability": "Medium",
            "immediate_urgency": "Immediate",
        },

        # Decisions
        "decisions": {
            "default_action": "Establish a weekly treasury review",
            "default_benefit": "Detect stress earlier and prioritize collections.",
            "default_justification": "Estimated runway {months} months — regular steering secures this position.",
            "default_horizon": "Next 30 days",
        },

        # Briefing
        "briefing": {
            "surplus_opportunity_title": "Enhance the value of treasury surplus",
            "surplus_opportunity_desc": "With {balance} in cash and collections covering spending pace, management can structure a minimum reserve and use the surplus.",
            "surplus_opportunity_benefit": "Improve cash yield without weakening operations.",
            "deficit_opportunity_title": "Accelerate confirmed collections",
            "deficit_opportunity_desc": "Prioritize follow-ups on open receivables to offset the {avg_net} daily burn.",
            "deficit_opportunity_benefit": "Reduce treasury pressure over the next 30 days.",
            "default_decision_action": "Steer treasury in management committee",
            "default_decision_horizon": "30 days",
        },
    },
    "ar": {
        "health": {
            "excellent": "صحة مالية ممتازة",
            "healthy": "وضع مالي جيد",
            "vigilance": "يتطلب المتابعة",
            "fragile": "وضع هش",
            "critical": "وضع حرج",
        },
        "resilience": {
            "excellent": "قوية جداً",
            "healthy": "قوية",
            "vigilance": "متوسطة",
            "fragile": "ضعيفة",
            "critical": "حرجة",
        },
        "severity": {
            "Critical": "حرج",
            "High": "مرتفع",
            "Medium": "متوسط",
            "Low": "منخفض",
        },
        "probability": {"high": "مرتفعة", "medium": "متوسطة", "low": "منخفضة"},
        "urgency": {"now": "فوري", "30": "خلال 30 يوماً", "month": "متابعة شهرية"},
        "health_explanation": "الأفق المقدر: {months} شهر. مستوى المخاطر: {risk_level}.",
        "resilience_interpretation_high": "قدرة قوية على امتصاص صدمة في الخزينة.",
        "resilience_interpretation_mid": "وضع قابل للإدارة مع متابعة منتظمة للتدفقات.",
        "resilience_interpretation_low": "هامش أمان محدود: يجب تخطيط إجراءات الإدارة.",
        "runway": "تغطي الخزينة حوالي {months} شهر من النشاط بالإيقاع الحالي.",
        "summary": "رصيد الخزينة {balance} — الصحة {health}/100، المرونة {resilience}/100، الأفق المقدر {runway_months} شهر. الخطر الرئيسي: {risk_title}. القرار ذو الأولوية: {decision_action}.",
        "financial": "خلال آخر 30 يوماً: التحصيلات {inflows}، المصروفات {outflows}، التدفق الصافي {net}. اتجاه الخزينة: {trend}.",
        "cash": "الأفق المقدر {months} شهر. المرونة: {label} ({score}/100).",
        "outlook": "خلال 30 يوماً: أقل رصيد متوقع حوالي {min_balance}، الاتجاه {trend}. مستوى المخاطر: {risk_level}.",
        "main_risk_title": "مخاطر الخزينة",
        "main_risk_desc": "يجب على الإدارة الحفاظ على رؤية واضحة للتدفقات والالتزامات الحرجة.",
        "opportunity_title": "تحسين الخزينة",
        "opportunity_desc": "هيكلة احتياطي أدنى واستخدام الفائض دون إضعاف العمليات.",
        "decision_action": "إجراء مراجعة أسبوعية للخزينة",
        "decision_rationale": "الإدارة المنتظمة تحمي وضع الخزينة وتسرع الاستجابة للضغوط.",
        "decision_outcome": "رؤية أفضل للتحصيلات والمصروفات وأولويات الدفع.",
        "deadline": "هذا الأسبوع",
        "alert_title": "ينصح بإدارة منتظمة",
        "alert_desc": "لا توجد إشارة حرجة فورية؛ الحفاظ على رؤية أسبوعية.",
        "alert_impact": "الحفاظ على قدرة الإدارة على الاستجابة.",
        "alert_action": "إجراء مراجعة أسبوعية للخزينة مع أهم التدفقات الداخلة والخارجة.",

        # Cash Runway
        "cash_runway": {
            "burn_rate_interpretation": "بإيقاع الاستهلاك الحالي ({avg_net} في اليوم)، تغطي الخزينة حوالي {months} شهر من النشاط.",
            "expense_coverage_interpretation": "الخزينة الحالية ({balance}) تغطي حوالي {months} شهر من المصروفات بإيقاع آخر 30 يوماً (التحصيلات الأخيرة: {monthly_inflows}).",
            "stable_buffer_interpretation": "خزينة متاحة {balance} دون تسجيل صرفات كبيرة في الفترة الأخيرة.",
            "insufficient_data_interpretation": "بيانات غير كافية لتقدير أفق الخزينة.",
            "declining_trend_adjustment": " تعديل حذر: الخزينة تتراجع خلال الفترة المرصودة.",
            "forecast_decline_adjustment": " المسار الأخير يقترح تشديد هامش الأمان.",
        },

        # Financial Health Drivers
        "health_drivers": {
            "runway": "الأفق المقدر: {months} شهر.",
            "positive_cashflow": "التدفق الصافي الأخير موجب.",
            "negative_cashflow": "التدفق الصافي الأخير سالب: {cashflow} في اليوم.",
            "risk_level": "مستوى المخاطر: {risk_level}.",
        },

        # Resilience Drivers
        "resilience_drivers": {
            "runway": "أفق الخزينة المقدر: {months} شهر.",
            "positive_cashflow": "التحصيلات تغطي إيقاع المصروفات الأخير.",
            "negative_cashflow": "استهلاك صافي {cashflow} في اليوم.",
            "improving_trend": "الخزينة تتحسن خلال الفترة المرصودة.",
            "declining_trend": "الخزينة تتراجع: اليقظة على هامش الأمان.",
            "outflow_spike": "المصروفات تزداد بنسبة {pct}% خلال 30 يوماً.",
            "inflow_drop": "التحصيلات تنخفض بنسبة {pct}% خلال 30 يوماً.",
        },

        # Alerts
        "alerts": {
            "critical_liquidity_title": "سيولة حرجة يجب التعامل معها اليوم",
            "critical_liquidity_desc": "الأفق المقدر فقط {days} يوماً ({interpretation})",
            "critical_liquidity_impact": "خطر تأخير في المدفوعات حوالي {amount}.",
            "critical_liquidity_action": "حظر الصرفات غير الأساسية، تفعيل متابعات العملاء وتأمين خط ائتمان.",
            "short_margin_title": "هامش خزينة قصير",
            "short_margin_impact": "قدرة ضئيلة على امتصاص دفعة عميل متأخرة أو مصروف غير متوقع.",
            "short_margin_action": "وضع خطة خزينة لمدة 30 يوماً مع أولويات الدفع.",
            "deterioration_title": "الخزينة تتفكك",
            "deterioration_desc": "متوسط الاستهلاك الصافي {avg_net} في اليوم خلال 30 يوماً.",
            "deterioration_impact": "تآكل مقدر حوالي {monthly_drain} كل شهر إذا لم يتغير شيء.",
            "deterioration_action": "تقليل التكاليف المتغيرة وتسريع التحصيلات المؤكدة.",
            "spending_spike_title": "زيادة غير طبيعية في المصروفات",
            "spending_spike_desc": "الصرفات زادت بنسبة {pct}% مقارنة بالفترة السابقة.",
            "spending_spike_impact": "تكلفة إضافية مقدرة حوالي {amount} خلال 30 يوماً.",
            "spending_spike_action": "التحقق من كل دفعة أعلى من الحد المعتاد وتأجيل المصروفات غير الحرجة.",
            "spending_accel_title": "تسارع في المصروفات",
            "spending_accel_desc": "الصرفات زادت بنسبة {pct}% خلال 30 يوماً.",
            "spending_accel_impact": "ضغط على هامش الخزينة المتاح.",
            "spending_accel_action": "مراجعة البنود المتغيرة ومواعيد الموردين.",
            "inflow_drop_title": "انخفاض حاد في التحصيلات",
            "inflow_drop_desc": "التحصيلات الأخيرة انخفضت بنسبة {pct}% — اعتماد متزايد على عدد قليل من التدفقات النقدية الداخلة.",
            "inflow_drop_impact": "عجز في الخزينة حوالي {amount} مقارنة بالشهر السابق.",
            "inflow_drop_action": "تحديد العملاء أو العقود المتأخرة وتأمين الفواتير عالية القيمة.",
            "inflow_slow_title": "تباطؤ في التحصيلات",
            "inflow_slow_desc": "التحصيلات انخفضت بنسبة {pct}% خلال 30 يوماً.",
            "inflow_slow_impact": "خطر ضغط على دورة الخزينة.",
            "inflow_slow_action": "متابعة الذمم المدينة المفتوحة وتأكيد تواريخ دفع العملاء.",
            "forecast_low_title": "نقطة منخفضة قادمة في الخزينة",
            "forecast_low_desc": "قد ينخفض مستوى الخزينة إلى حوالي {min_balance}.",
            "forecast_low_impact": "فجوة محتملة حوالي {amount} مقارنة بالرصيد الحالي.",
            "forecast_low_action": "تخطيط التحصيلات وتأجيل المدفوعات قبل أسبوع الضغوط.",
            "opportunity_title": "فرصة: تحسين فائض الخزينة",
            "opportunity_desc": "خزينة {balance} مع توليد نقدي موجب.",
            "opportunity_impact": "تحسين عائد النقد الفائض دون إضعاف العمليات.",
            "opportunity_action": "تحديد احتياطي تشغيلي أدنى وتخصيص الفائض (تسديد دين، استثمار قصير الأجل).",
        },

        # Risks
        "risks": {
            "default_title": "مخاطر الخزينة",
            "high_probability": "مرتفعة",
            "medium_probability": "متوسطة",
            "immediate_urgency": "فوري",
        },

        # Decisions
        "decisions": {
            "default_action": "إقامة مراجعة أسبوعية للخزينة",
            "default_benefit": "اكتشاف الضغوط مبكراً وتحديد أولويات التحصيلات.",
            "default_justification": "الأفق المقدر {months} شهر — الإدارة المنتظمة تحمي هذا الوضع.",
            "default_horizon": "الـ 30 يوماً القادمة",
        },

        # Briefing
        "briefing": {
            "surplus_opportunity_title": "تعزيز قيمة فائض الخزينة",
            "surplus_opportunity_desc": "مع {balance} نقداً وتحصيلات تغطي إيقاع المصروفات، يمكن للإدارة هيكلة احتياطي أدنى واستخدام الفائض.",
            "surplus_opportunity_benefit": "تحسين عائد النقد دون إضعاف العمليات.",
            "deficit_opportunity_title": "تسريع التحصيلات المؤكدة",
            "deficit_opportunity_desc": "تحديد أولويات المتابعات على الذمم المدينة المفتوحة لتعويض استهلاك {avg_net} اليومي.",
            "deficit_opportunity_benefit": "تقليل ضغط الخزينة خلال الـ 30 يوماً القادمة.",
            "default_decision_action": "إدارة الخزينة في لجنة الإدارة",
            "default_decision_horizon": "30 يوماً",
        },
    },
}


def _catalog(locale: str) -> dict:
    return _TEXT.get(normalize_locale(locale), _TEXT[DEFAULT_LOCALE])


def get_bi_translation(key: str, locale: str, **kwargs) -> str:
    """Get a translated string with safe fallbacks."""
    locale = normalize_locale(locale)
    catalog = _catalog(locale)
    # Navigate nested keys
    parts = key.split(".")
    value = catalog
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            # Fallback to French
            catalog_fr = _TEXT["fr"]
            value_fr = catalog_fr
            for part_fr in parts:
                if isinstance(value_fr, dict) and part_fr in value_fr:
                    value_fr = value_fr[part_fr]
                else:
                    return key
            value = value_fr
            break
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return value if isinstance(value, str) else key


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
    if not isinstance(payload, dict):
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
            balance=_money(runway.get("avg_daily_inflow", 0)),  # This is just a placeholder, we'll fix in the service
            health=score,
            resilience=res_score,
            runway_months=months,
            risk_title=text["main_risk_title"],
            decision_action=text["decision_action"],
        )
        briefing["executive_briefing"] = briefing["executive_summary"]
        briefing["financial_situation"] = text["financial"].format(
            inflows=inflows,
            outflows=outflows,
            net=net,
            trend="stable"
        )
        briefing["cash_position_analysis"] = text["cash"].format(
            months=months,
            label=resilience["label"],
            score=res_score,
        )
        briefing["outlook_30_days"] = text["outlook"].format(
            min_balance=_money(0),
            trend="stable",
            risk_level=risk_level
        )
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
