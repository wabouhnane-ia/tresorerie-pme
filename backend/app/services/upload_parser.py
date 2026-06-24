"""Parse uploaded CSV/XLSX/PDF into normalized financial records."""

from typing import Any, Tuple
from io import BytesIO

import pandas as pd

from app.services import mapping_utils

from app.core.locale import DEFAULT_LOCALE, normalize_locale


COLUMN_ALIASES = {
    "date": ["date", "ds", "jour", "day", "date_operation", "date opération", "date_opération"],
    "cash_inflow": [
        "cash_inflow",
        "daily_revenue",
        "revenue",
        "encaissements",
        "encaissements client",
        "encaissements clients",
        "encaissements_client",
        "encaissement client",
        "règlements clients",
        "reglements clients",
        "encaissements_ttc",
        "encaissements ttc",
        "recettes",
        "ca",
        "sales",
        "income",
        "inflow",
        "credits",
        "collections",
        "proceeds",
        "encais",
        "recette",
        "entree",
        "credit",
        "vente",
        "revenus_journaliers",
    ],
    "cash_outflow": [
        "cash_outflow",
        "total_expenses",
        "expenses",
        "decaissements",
        "paiements fournisseur",
        "paiements fournisseurs",
        "paiements_fournisseurs",
        "règlements fournisseurs",
        "règlements fournisseurs",
        "reglements fournisseurs",
        "charges",
        "depenses",
        "costs",
        "payments",
        "outflow",
        "debits",
        "disbursements",
        "expenditures",
        "spending",
        "decais",
        "depense",
        "charge",
        "sortie",
        "debit",
        "charges_totales",
    ],
    "net_cashflow": ["net_cashflow", "cashflow", "flux_net", "net_cash_flow"],
    "treasury_balance": [
        "treasury_balance",
        "treasury",
        "tresorerie",
        "solde",
        "solde bancaire",
        "solde_bancaire",
        "balance",
    ],
    "number_of_clients": ["number_of_clients", "clients", "nb_clients"],
    "scheduled_receipts": [
        "scheduled_receipts",
        "receipts_scheduled",
        "encaissements_planifies",
        "encaissements_planifié",
        "receipts",
    ],
    "overdue_receipts": [
        "overdue_receipts",
        "receipts_overdue",
        "encaissements_en_retard",
        "encaissements_retard",
    ],
    "scheduled_payments": [
        "scheduled_payments",
        "payments_scheduled",
        "paiements_planifies",
        "paiements_planifié",
        "payments",
    ],
    "overdue_payments": [
        "overdue_payments",
        "payments_overdue",
        "paiements_en_retard",
        "paiements_retard",
    ],
}

REQUIRED_COLUMNS = ["date", "cash_inflow", "cash_outflow", "treasury_balance", "scheduled_receipts", "overdue_receipts", "scheduled_payments", "overdue_payments"]

LOCALE_COLUMN_ALIASES = {
    "ar": {
        "date": ["تاريخ", "التاريخ", "يوم"],
        "cash_inflow": [
            "إيرادات",
            "الإيرادات",
            "تحصيلات",
            "مدخول",
            "دخل",
            "مقبوضات",
            "encaissements",
        ],
        "cash_outflow": [
            "مصروفات",
            "المصروفات",
            "نفقات",
            "مدفوعات",
            "مصاريف",
            "decaissements",
        ],
        "treasury_balance": ["رصيد", "الرصيد", "خزينة", "tresorerie", "solde"],
    },
    "en": {
        "date": ["date", "operation date", "transaction date"],
        "cash_inflow": ["inflow", "inflows", "collections", "receipts", "credits"],
        "cash_outflow": ["outflow", "outflows", "payments", "debits", "spend"],
    },
}


class MissingColumnsError(ValueError):
    def __init__(self, missing_columns: list[str], suggestions: dict | None = None):
        self.missing_columns = missing_columns
        self.suggestions = suggestions or {}
        super().__init__(f"Missing required columns: {', '.join(missing_columns)}")


def _aliases_for_locale(locale: str) -> dict[str, list[str]]:
    loc = normalize_locale(locale)
    merged: dict[str, list[str]] = {k: list(v) for k, v in COLUMN_ALIASES.items()}
    extra = LOCALE_COLUMN_ALIASES.get(loc, {})
    for standard, aliases in extra.items():
        merged.setdefault(standard, [])
        for alias in aliases:
            if alias not in merged[standard]:
                merged[standard].append(alias)
    return merged


def detect_columns(df: pd.DataFrame, locale: str = DEFAULT_LOCALE, return_report: bool = False) -> dict | Tuple[dict, dict]:
    """
    Map DataFrame columns to standard names.
    Returns a dict {standard_name: original_column_name}.

    If `return_report` is True, returns (mapping, report) where report contains
    per-column confidences and a `mapping_quality_score` (0-100).
    """
    original_cols = list(df.columns)
    cols_lower = [str(c).strip().lower() for c in original_cols]
    mapping: dict[str, str] = {}
    aliases_map = _aliases_for_locale(locale)

    per_column: dict[str, dict] = {str(c): {"matched_to": None, "method": None, "score": 0} for c in original_cols}

    # 1) Exact alias match against lowered column names (backwards compatible)
    for standard, aliases in aliases_map.items():
        for alias in aliases:
            if alias in cols_lower:
                idx = cols_lower.index(alias)
                mapping[standard] = original_cols[idx]
                per_column[original_cols[idx]] = {"matched_to": standard, "method": "exact", "score": 100}
                break

    # 2) Canonicalized alias matching (normalize accents / punctuation)
    # Build canonical alias sets
    canonical_aliases = {s: [mapping_utils.normalize_column_name(a) for a in aliases_map[s]] for s in aliases_map}
    canonical_cols = {col: mapping_utils.normalize_column_name(col) for col in original_cols}

    for standard in aliases_map:
        if standard in mapping:
            continue
        for alias_canon in canonical_aliases[standard]:
            for col, col_canon in canonical_cols.items():
                if col_canon == alias_canon and standard not in mapping and col not in mapping.values():
                    mapping[standard] = col
                    per_column[col] = {"matched_to": standard, "method": "canonical", "score": 100}
                    break
            if standard in mapping:
                break

    # 3) Fuzzy matching (only for remaining unmapped standards and unmapped columns)
    unmapped_standards = [s for s in aliases_map if s not in mapping]
    unmapped_cols = [c for c in original_cols if per_column[c]["matched_to"] is None]

    for standard in unmapped_standards:
        best_col = None
        best_score = 0
        best_alias = None
        for col in unmapped_cols:
            # compute best score comparing original col name against aliases
            for alias in aliases_map[standard]:
                score = mapping_utils.fuzzy_score(col, alias)
                if score > best_score:
                    best_score = score
                    best_col = col
                    best_alias = alias
        if best_col and best_score > 0:
            # Register fuzzy mapping; don't override existing mappings
            if standard not in mapping and best_col not in mapping.values():
                mapping[standard] = best_col
                per_column[best_col] = {"matched_to": standard, "method": "fuzzy", "score": int(best_score)}
                # remove from unmapped_cols to avoid double assignment
                if best_col in unmapped_cols:
                    unmapped_cols.remove(best_col)

    # Build report
    report = {"per_column": per_column, "mapping": mapping, "mapping_quality_score": 100}

    # Compute mapping_quality_score based on REQUIRED_COLUMNS only
    weights = []
    for req in REQUIRED_COLUMNS:
        if req in mapping:
            col = mapping[req]
            entry = per_column.get(col, {})
            if entry.get("method") in ("exact", "canonical"):
                weights.append(1.0)
            else:
                weights.append((entry.get("score", 0) or 0) / 100.0)
        else:
            weights.append(0.0)

    if weights:
        report_score = int(round(100 * (sum(weights) / len(weights))))
    else:
        report_score = 0

    report["mapping_quality_score"] = report_score

    # Suggestions for missing required columns
    suggestions = {}
    for req in REQUIRED_COLUMNS:
        if req not in mapping:
            # Suggest best fuzzy candidate among original columns
            best_col = None
            best_score = 0
            best_alias = None
            for col in original_cols:
                for alias in aliases_map.get(req, []):
                    score = mapping_utils.fuzzy_score(col, alias)
                    if score > best_score:
                        best_score = score
                        best_col = col
                        best_alias = alias
            if best_col:
                suggestions[req] = {"suggested_column": best_col, "score": int(best_score), "matched_alias": best_alias}

    report["suggestions"] = suggestions

    if return_report:
        return mapping, report

    return mapping


def validate_required_columns(mapping: dict[str, str], suggestions: dict | None = None) -> None:
    """
    Validate that all required columns are present.
    Raises MissingColumnsError if any are missing.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in mapping]
    if missing:
        raise MissingColumnsError(missing, suggestions=suggestions)


def normalize_financial_dataframe(df: pd.DataFrame, locale: str = DEFAULT_LOCALE) -> pd.DataFrame:
    """
    Detects columns, validates, cleans and normalizes to a standard structure.
    Handles both dot (.) and comma (,) as decimal separators.
    Strictly enforces V2.0 business data schema with all commitment columns.
    """
    mapping, report = detect_columns(df, locale=locale, return_report=True)
    
    # Strictly validate ALL required V2.0 columns
    validate_required_columns(mapping, suggestions=report.get("suggestions"))

    out = pd.DataFrame()

    # Required: Date
    out["date"] = pd.to_datetime(df[mapping["date"]], errors="coerce")
    out = out.dropna(subset=["date"])

    # Financial fields (all V2.0 required fields)
    fields = {
        "cash_inflow": "cash_inflow",
        "cash_outflow": "cash_outflow",
        "net_cashflow": "net_cashflow",
        "treasury_balance": "treasury_balance",
        "scheduled_receipts": "scheduled_receipts",
        "overdue_receipts": "overdue_receipts",
        "scheduled_payments": "scheduled_payments",
        "overdue_payments": "overdue_payments",
    }

    for standard, internal in fields.items():
        if standard in mapping:
            # Convert to string, replace comma with dot for decimal separator
            col_data = df[mapping[standard]].astype(str).str.replace(",", ".", regex=False)
            out[internal] = pd.to_numeric(col_data, errors="coerce").fillna(0)

    # Logic for missing optional fields
    if "net_cashflow" not in mapping:
        out["net_cashflow"] = out["cash_inflow"] - out["cash_outflow"]

    # Add dataset version
    out["dataset_version"] = "2.0"

    return out.sort_values("date").reset_index(drop=True)


def dataframe_to_flat_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Converts normalized DataFrame to a list of flat dicts for MongoDB.
    """
    records = []
    for _, row in df.iterrows():
        record = {
            "date": row["date"].to_pydatetime(),  # Convert to Python datetime for MongoDB ISODate
            "cash_inflow": float(row["cash_inflow"]),
            "cash_outflow": float(row["cash_outflow"]),
            "net_cashflow": float(row["net_cashflow"]),
            "treasury_balance": float(row["treasury_balance"]),
            "scheduled_receipts": float(row.get("scheduled_receipts", 0)),
            "overdue_receipts": float(row.get("overdue_receipts", 0)),
            "scheduled_payments": float(row.get("scheduled_payments", 0)),
            "overdue_payments": float(row.get("overdue_payments", 0)),
        }
        if "dataset_version" in row:
            record["dataset_version"] = row["dataset_version"]
        records.append(record)
    return records


def parse_financial_file(
    file_content: bytes,
    filename: str,
    locale: str = DEFAULT_LOCALE,
) -> pd.DataFrame:
    """
    Parse CSV, Excel, or PDF file from bytes into a normalized DataFrame.

    Args:
        file_content: Raw file bytes
        filename: Original filename (used to detect format)
        locale: User locale for column header matching (fr, en, ar)

    Returns:
        Normalized DataFrame with standard columns

    Raises:
        ValueError: If file format is unsupported
        MissingColumnsError: If required columns are missing
    """
    filename_lower = filename.lower()
    locale = normalize_locale(locale)

    if filename_lower.endswith(".csv"):
        df = pd.read_csv(BytesIO(file_content))
        return normalize_financial_dataframe(df, locale=locale)
    if filename_lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(file_content))
        return normalize_financial_dataframe(df, locale=locale)
    if filename_lower.endswith(".pdf"):
        from app.services.pdf_parser import parse_financial_pdf

        return parse_financial_pdf(file_content, locale=locale)

    raise ValueError(
        f"Unsupported file format: {filename}. Supported formats: .csv, .xlsx, .xls, .pdf"
    )
