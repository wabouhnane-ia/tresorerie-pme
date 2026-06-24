from app.reporting.pdf_report import generate_executive_pdf_report

bi = {
    "financial_health_score": {"score": 72, "label": "vigilance"},
    "treasury_resilience_score": {"score": 58, "label": "fragile"},
    "cash_runway": {"days": 45, "months": 1, "level": "fragile"},
    "period": "01/01/2026 - 31/03/2026",
    "executive_briefing": {
        "executive_summary": "La trésorerie nécessite des mesures rapides pour sécuriser le fonds de roulement.",
        "immediate_actions": [
            {"action": "Négocier un délai fournisseurs de 30 jours", "why": "Réduire sorties immédiates", "deadline": "7 jours"},
            {"action": "Prioriser encaissements clients majeurs", "why": "Améliorer cash disponible", "deadline": "14 jours"},
        ],
        "main_risk": {"title": "Retards encaissements", "description": "Clients clés retardent paiements"},
        "main_opportunity": {"title": "Remises fournisseurs", "description": "Négocier escomptes"},
        "recommended_decision": {"action": "Activer ligne de crédit court terme", "rationale": "Couverture 60 jours"},
    },
    "smart_alerts": [{"title": "Baisse encaissements semaine N", "severity": "high"}],
    "top_risks": [{"title": "Perte client X", "probability": "medium"}],
    "top_decisions": [{"action": "Suspendre dépenses non essentielles", "expected_benefit": "Économies 15%"}],
}

# Previous BI snapshot for historical comparison
previous_bi = {
    "financial_health_score": {"score": 67, "label": "vigilance"},
    "treasury_resilience_score": {"score": 40, "label": "fragile"},
    "cash_runway": {"days": 27, "months": 0, "level": "critical"},
}

pdf = generate_executive_pdf_report(
    company_name="ACME SARL", 
    business_intelligence=bi, 
    treasury_trend="stable",
    previous_business_intelligence=previous_bi,
)
with open("../outputs/executive_report_v2_sample.pdf", "wb") as f:
    f.write(pdf)
print("Wrote ../outputs/executive_report_v2_sample.pdf")
print("KPI cards should show deltas:")
print("  - Santé financière: 72 / 100 (+5 points)")
print("  - Résilience: 58 / 100 (+18 points)")
print("  - Horizon trésorerie: 45 jours (+18 jours)")
