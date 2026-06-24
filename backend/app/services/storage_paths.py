"""Filesystem paths for tenant-isolated storage."""

from pathlib import Path

from app.core.config import settings


def company_root(company_id: str) -> Path:
    path = Path(settings.STORAGE_ROOT) / "companies" / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def upload_dir(company_id: str, upload_id: str) -> Path:
    path = company_root(company_id) / "uploads" / upload_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_path(company_id: str, report_id: str) -> Path:
    path = company_root(company_id) / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{report_id}.pdf"


def forecast_artifact_dir(company_id: str, run_id: str) -> Path:
    path = company_root(company_id) / "forecasts" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path
