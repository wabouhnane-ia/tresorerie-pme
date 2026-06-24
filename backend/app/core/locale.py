"""Locale resolution for API, services, LLM and reporting."""

from __future__ import annotations

from fastapi import Header, Query

DEFAULT_LOCALE = "fr"
SUPPORTED_LOCALES = frozenset({"fr", "en", "ar"})


def normalize_locale(value: str | None = None) -> str:
    if not value:
        return DEFAULT_LOCALE

    for raw_part in str(value).split(","):
        code = raw_part.strip().split(";")[0].strip().lower()
        if not code:
            continue
        primary = code.replace("_", "-").split("-")[0]
        if primary in SUPPORTED_LOCALES:
            return primary

    return DEFAULT_LOCALE


def resolve_locale(
    x_locale: str | None = Header(None, alias="X-Locale"),
    accept_language: str | None = Header(None, alias="Accept-Language"),
    locale: str | None = Query(None),
) -> str:
    return normalize_locale(locale or x_locale or accept_language)
