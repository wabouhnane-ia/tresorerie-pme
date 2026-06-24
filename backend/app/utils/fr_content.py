"""Backward-compatible French normalization (prefer locale_content)."""

from app.utils.locale_content import (
    DEFAULT_LOCALE,
    disclaimer_for_locale,
    normalize_executive_analysis,
    normalize_recommendation_item,
    normalize_risk_entry,
    normalize_risk_intelligence,
    normalize_time_horizon,
)

__all__ = [
    "DEFAULT_LOCALE",
    "disclaimer_for_locale",
    "normalize_executive_analysis",
    "normalize_recommendation_item",
    "normalize_risk_entry",
    "normalize_risk_intelligence",
    "normalize_time_horizon",
]
