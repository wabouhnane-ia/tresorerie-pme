"""Dataset Deduplication Service.

Provides functions to detect duplicate datasets based on content rather than filename.
This prevents users from uploading the same financial data multiple times.

Key features:
- File-level deduplication (SHA256 of raw bytes)
- Dataset-level deduplication (SHA256 of normalized DataFrame content)
- Robust normalization that handles column order, float precision, and NaN variations
"""

import hashlib
import json
import logging
from typing import Optional

import pandas as pd
from app.utils.bson_utils import ObjectId

from app.db import collections as c
from app.db.mongodb import database

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: File-level deduplication
# ──────────────────────────────────────────────────────────────────────────────

def compute_file_hash(file_bytes: bytes) -> str:
    """
    Generate SHA256 hash from raw uploaded file bytes.
    
    This catches exact file duplicates (same filename, same content).
    
    Args:
        file_bytes: Raw bytes of the uploaded file
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    return hashlib.sha256(file_bytes).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: DataFrame normalization
# ──────────────────────────────────────────────────────────────────────────────

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a DataFrame to ensure consistent representation.
    
    The goal is that the same dataset produces the same normalized representation
    even if:
    - Column names have different casing or whitespace
    - Rows are in different order
    - Float precision varies slightly
    - NaN values are represented differently
    
    Args:
        df: Input DataFrame to normalize
        
    Returns:
        Normalized DataFrame
    """
    if df.empty:
        return df.copy()
    
    # Create a copy to avoid modifying the original
    normalized = df.copy()
    
    # 1. Lowercase and strip column names
    normalized.columns = [str(col).lower().strip() for col in normalized.columns]
    
    # 2. Sort columns alphabetically for consistent order
    normalized = normalized.reindex(sorted(normalized.columns), axis=1)
    
    # 3. Identify the date column (common variations)
    date_column = None
    date_candidates = ['date', 'created_at', 'timestamp', 'time', 'day']
    
    for candidate in date_candidates:
        if candidate in normalized.columns:
            date_column = candidate
            break
    
    # 4. Sort by date column if found, otherwise by first column
    if date_column:
        try:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(normalized[date_column]):
                normalized[date_column] = pd.to_datetime(normalized[date_column], errors='coerce')
            normalized = normalized.sort_values(by=date_column)
        except Exception as e:
            logger.warning(f"Could not sort by date column '{date_column}': {e}")
            # Fallback: sort by first column
            normalized = normalized.sort_values(by=normalized.columns[0])
    else:
        # Sort by first column as fallback
        normalized = normalized.sort_values(by=normalized.columns[0])
    
    # 5. Normalize NaN values - replace all NaN variants with pd.NA
    normalized = normalized.fillna(pd.NA)
    
    # 6. Normalize float precision to 6 decimal places
    for col in normalized.columns:
        if pd.api.types.is_numeric_dtype(normalized[col]):
            # Round floats to 6 decimal places to handle precision differences
            normalized[col] = normalized[col].round(6)
    
    # 7. Reset index to ensure consistent indexing
    normalized = normalized.reset_index(drop=True)
    
    logger.debug(f"Normalized DataFrame: {normalized.shape} rows x {len(normalized.columns)} columns")
    return normalized


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: Dataset-level deduplication
# ──────────────────────────────────────────────────────────────────────────────

def compute_dataset_hash(df: pd.DataFrame) -> str:
    """
    Generate SHA256 hash from normalized DataFrame content.
    
    This catches semantic duplicates - same data with different formatting,
    column order, or minor variations.
    
    Args:
        df: Input DataFrame
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    try:
        # 1. Normalize the DataFrame
        normalized_df = normalize_dataframe(df)
        
        # 2. Convert to stable JSON representation
        json_str = normalized_df.to_json(
            orient='records',
            date_format='iso',
            double_precision=6
        )
        
        # 3. Parse and re-serialize to ensure consistent key ordering
        import json
        parsed = json.loads(json_str)
        # Sort keys in each record for consistency
        sorted_records = [dict(sorted(record.items())) for record in parsed]
        # Re-serialize with sorted keys
        json_str = json.dumps(sorted_records, sort_keys=True)
        
        # 4. Generate SHA256 hash
        dataset_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        
        logger.debug(f"Generated dataset hash: {dataset_hash[:16]}... for DataFrame with {len(df)} rows")
        return dataset_hash
        
    except Exception as e:
        logger.error(f"Failed to compute dataset hash: {e}")
        # Fallback: use string representation
        fallback_str = str(df.values.tolist())
        return hashlib.sha256(fallback_str.encode('utf-8')).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4: MongoDB duplicate detection
# ──────────────────────────────────────────────────────────────────────────────

async def find_duplicate_dataset(
    company_id: str, 
    dataset_hash: str
) -> Optional[dict]:
    """
    Search for existing upload with the same dataset hash for this company.
    
    Args:
        company_id: Company ID (string or ObjectId)
        dataset_hash: SHA256 hash of the normalized dataset
        
    Returns:
        Upload document if duplicate found, None otherwise
    """
    try:
        # Ensure company_id is ObjectId for MongoDB query
        if isinstance(company_id, str):
            company_id = ObjectId(company_id)
        
        # Search for existing upload with same company_id and dataset_hash
        duplicate = await database[c.UPLOADS].find_one({
            "company_id": company_id,
            "dataset_hash": dataset_hash,
            "status": {"$ne": "failed"}  # Exclude failed uploads
        })
        
        if duplicate:
            logger.info(
                f"Found duplicate dataset: {dataset_hash[:16]}... "
                f"for company {company_id} (original upload: {duplicate['_id']})"
            )
            return duplicate
        
        logger.debug(f"No duplicate found for dataset hash: {dataset_hash[:16]}...")
        return None
        
    except Exception as e:
        logger.error(f"Error searching for duplicate dataset: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────────────────────

async def find_duplicate_file(
    company_id: str, 
    file_hash: str
) -> Optional[dict]:
    """
    Search for existing upload with the same file hash for this company.
    
    This is a stricter check than dataset deduplication - it catches
    exact file duplicates.
    
    Args:
        company_id: Company ID (string or ObjectId)
        file_hash: SHA256 hash of the raw file bytes
        
    Returns:
        Upload document if duplicate found, None otherwise
    """
    try:
        if isinstance(company_id, str):
            company_id = ObjectId(company_id)
        
        duplicate = await database[c.UPLOADS].find_one({
            "company_id": company_id,
            "file_hash": file_hash,
            "status": {"$ne": "failed"}
        })
        
        if duplicate:
            logger.info(
                f"Found duplicate file: {file_hash[:16]}... "
                f"for company {company_id} (original upload: {duplicate['_id']})"
            )
            return duplicate
        
        return None
        
    except Exception as e:
        logger.error(f"Error searching for duplicate file: {e}")
        return None


def get_deduplication_summary(df: pd.DataFrame, file_bytes: bytes) -> dict:
    """
    Generate a summary of deduplication hashes for a dataset.
    
    Useful for debugging and logging.
    
    Args:
        df: DataFrame to analyze
        file_bytes: Raw file bytes
        
    Returns:
        Dictionary with hash information and dataset stats
    """
    return {
        "file_hash": compute_file_hash(file_bytes),
        "dataset_hash": compute_dataset_hash(df),
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "normalized_columns": [str(col).lower().strip() for col in df.columns],
    }


async def process_upload_deduplication(
    company_id: str,
    file_bytes: bytes,
    extension: str,
    filename: str = None,
    locale: str = "fr",
) -> tuple[str, str, pd.DataFrame, dict | None]:
    """
    Process file for deduplication detection.
    
    This is a convenience function that combines file parsing, normalization,
    hash computation, and duplicate detection in one call.
    
    Args:
        company_id: Company ID for duplicate search
        file_bytes: Raw file bytes
        extension: File extension (.csv, .xlsx)
        filename: Original filename (optional, defaults to extension if not provided)
        
    Returns:
        Tuple of (file_hash, dataset_hash, normalized_df, duplicate_upload_or_none)
        
    Raises:
        Exception: If file parsing fails
    """
    from app.services.upload_parser import parse_financial_file
    
    # Compute file hash
    file_hash = compute_file_hash(file_bytes)
    
    # Use filename if provided, otherwise construct from extension
    parse_filename = filename if filename else f"data{extension}"
    
    # Parse and normalize DataFrame
    df = parse_financial_file(file_bytes, parse_filename, locale=locale)
    normalized_df = normalize_dataframe(df)
    dataset_hash = compute_dataset_hash(normalized_df)
    
    # Check for duplicates
    duplicate_upload = await find_duplicate_dataset(company_id, dataset_hash)
    
    logger.debug(
        f"Deduplication processed: file_hash={file_hash[:16]}..., "
        f"dataset_hash={dataset_hash[:16]}..., duplicate={'Yes' if duplicate_upload else 'No'}"
    )
    
    return file_hash, dataset_hash, normalized_df, duplicate_upload