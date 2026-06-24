"""Mapping helpers: normalization and fuzzy matching.

Keep this module lightweight and isolated so mapping logic can evolve.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Tuple, Optional

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback when rapidfuzz not installed
    fuzz = None


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_column_name(name: str) -> str:
    """Canonicalize column header for robust matching.

    - lowercases
    - removes accents/diacritics
    - replaces non-alphanumeric chars with single spaces
    - collapses spaces
    """
    if name is None:
        return ""
    s = str(name).strip().lower()
    # remove accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # replace non-alphanumeric with space
    s = _NON_ALNUM.sub(" ", s)
    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fuzzy_score(a: str, b: str) -> int:
    """Return integer similarity score 0-100 using rapidfuzz when available.

    If rapidfuzz not available, fall back to a simple heuristic using
    normalized equality.
    """
    if not a or not b:
        return 0
    if fuzz is None:
        # fallback: exact equality of normalized strings
        return 100 if normalize_column_name(a) == normalize_column_name(b) else 0

    # use token_set_ratio for robust token order invariance
    try:
        return int(fuzz.token_set_ratio(a, b))
    except Exception:
        try:
            return int(fuzz.ratio(a, b))
        except Exception:
            return 0


def best_fuzzy_match(candidate: str, choices: Iterable[str]) -> Tuple[Optional[str], int]:
    """Return the best match from choices and its score.

    Returns (None, 0) if no choices.
    """
    best = None
    best_score = 0
    for ch in choices:
        score = fuzzy_score(candidate, ch)
        if score > best_score:
            best_score = score
            best = ch
    return best, best_score
