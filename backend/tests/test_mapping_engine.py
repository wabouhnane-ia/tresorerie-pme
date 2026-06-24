import pandas as pd
import pytest

from app.services.upload_parser import detect_columns, normalize_financial_dataframe, MissingColumnsError


def df_from_cols(cols):
    # Build minimal DataFrame with given column names and one row of sample data
    data = {c: ["1"] for c in cols}
    return pd.DataFrame(data)


def test_exact_match_columns():
    cols = ["Date", "Encaissements TTC", "Charges"]
    df = df_from_cols(cols)
    mapping, report = detect_columns(df, locale="fr", return_report=True)
    assert "date" in mapping
    assert "cash_inflow" in mapping
    assert "cash_outflow" in mapping
    assert report["mapping_quality_score"] == 100


def test_fuzzy_and_suggestions():
    cols = ["Date opération", "Encaissements_Client", "Paiements_Fournisseurs"]
    df = df_from_cols(cols)
    mapping, report = detect_columns(df, locale="fr", return_report=True)
    # We expect fuzzy matching to produce candidates for required columns
    assert report["mapping_quality_score"] >= 80
    # Ensure per-column entries exist
    for c in cols:
        assert c in report["per_column"]


def test_normalize_financial_dataframe_raises_with_suggestions():
    # Missing cash_outflow — should raise with suggestions
    cols = ["Date opération", "Encaissements_Client"]
    df = df_from_cols(cols)
    # Pass through normalize_financial_dataframe which uses detect_columns and raises
    with pytest.raises(MissingColumnsError) as excinfo:
        normalize_financial_dataframe(df, locale="fr")
    exc = excinfo.value
    assert isinstance(exc.suggestions, dict)
    assert "cash_outflow" in exc.suggestions
