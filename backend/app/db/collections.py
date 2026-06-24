"""MongoDB collection names (single source of truth)."""

# Core collections
USERS = "users"
COMPANIES = "companies"
MEMBERSHIPS = "memberships"

# SaaS billing
SUBSCRIPTION_PLANS = "subscription_plans"

# Legacy billing (unused)
PLANS = "plans"
PAYMENTS = "payments"

# Sprint 9: company-level SaaS subscriptions
SUBSCRIPTIONS = "subscriptions"

# Data management
UPLOADS = "uploads"
FINANCIAL_RECORDS = "financial_records"
DATA_QUALITY_REPORTS = "data_quality_reports"

# Treasury Intelligence (PHASE 1 — obsolete, superseded by company_treasury_profiles)
TREASURY_PROFILES = "treasury_profiles"

# PHASE 3: Continuous Treasury History Platform
COMPANY_TREASURY_PROFILES = "company_treasury_profiles"

# PHASE 2A: Intelligent column mapping (API removed — collection retained for legacy data)
COMPANY_MAPPING_PROFILES = "company_mapping_profiles"

# Forecasting and analytics
FORECAST_RUNS = "forecast_runs"
FORECASTS = "forecasts"
RISK_ASSESSMENTS = "risk_assessments"
RECOMMENDATIONS = "recommendations"
AI_INSIGHTS = "ai_insights"
DECISION_HISTORY = "decision_history"

# Sprint 8: Notifications & Alert Center
NOTIFICATIONS = "notifications"

# Audit and compliance
AUDIT_LOGS = "audit_logs"
