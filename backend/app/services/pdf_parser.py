"""Extract tabular treasury data from PDF uploads (locale-aware column detection)."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from app.core.locale import DEFAULT_LOCALE, normalize_locale
from app.services.upload_parser import normalize_financial_dataframe


def _tables_from_pdf(file_content: bytes) -> list[pd.DataFrame]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError(
            "PDF support is not installed on the server (pdfplumber). "
            "Use CSV or Excel, or contact support."
        ) from exc

    frames: list[pd.DataFrame] = []
    with pdfplumber.open(BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header = [str(c or "").strip() for c in table[0]]
                rows = table[1:]
                if not any(header):
                    continue
                df = pd.DataFrame(rows, columns=header)
                if len(df.columns) >= 3 and len(df) >= 1:
                    frames.append(df)
    return frames


def parse_financial_pdf(file_content: bytes, locale: str = DEFAULT_LOCALE) -> pd.DataFrame:
    """
    Parse a treasury PDF by extracting the first suitable table.
    Column matching uses locale-aware aliases from upload_parser.
    """
    locale = normalize_locale(locale)
    frames = _tables_from_pdf(file_content)
    if not frames:
        raise ValueError(
            "No readable table found in PDF. Export your data as CSV/Excel or use a PDF with a clear table."
        )

    best = max(frames, key=lambda df: len(df) * len(df.columns))
    return normalize_financial_dataframe(best, locale=locale)
