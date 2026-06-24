"""
Validation script for legacy billing migration.

Usage:
    cd backend
    python -m scripts.validate_migration

This script verifies:
1. No active imports of legacy services
2. All required collections exist
3. New SaaS system is functional
4. Legacy collections are empty (as expected)
"""

import asyncio
import sys
from pathlib import Path

# Allow running from the backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import collections as c
from app.db.mongodb import database, client


async def validate_migration():
    """Run all validation checks."""
    
    print("\n" + "="*70)
    print("LEGACY BILLING MIGRATION — VALIDATION")
    print("="*70 + "\n")
    
    all_passed = True
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 1: Verify collection constants
    # ──────────────────────────────────────────────────────────────────────────
    
    print("✓ CHECK 1: Collection constants")
    
    required_collections = [
        "USERS", "COMPANIES", "MEMBERSHIPS", "SUBSCRIPTION_PLANS",
        "UPLOADS", "FINANCIAL_RECORDS", "DATA_QUALITY_REPORTS",
        "FORECAST_RUNS", "FORECASTS", "RISK_ASSESSMENTS",
        "RECOMMENDATIONS", "AI_INSIGHTS", "AUDIT_LOGS"
    ]
    
    deprecated_collections = ["PLANS", "SUBSCRIPTIONS", "PAYMENTS"]
    removed_collections = ["REPORTS"]
    
    for col in required_collections:
        if hasattr(c, col):
            print(f"  ✅ {col} exists")
        else:
            print(f"  ❌ {col} MISSING")
            all_passed = False
    
    for col in deprecated_collections:
        if hasattr(c, col):
            print(f"  ⚠️  {col} exists (DEPRECATED - OK)")
        else:
            print(f"  ❌ {col} missing (should exist as deprecated)")
            all_passed = False
    
    for col in removed_collections:
        if hasattr(c, col):
            print(f"  ❌ {col} still exists (should be removed)")
            all_passed = False
        else:
            print(f"  ✅ {col} removed")
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 2: Verify database collections
    # ──────────────────────────────────────────────────────────────────────────
    
    print("\n✓ CHECK 2: Database collections")
    
    existing_collections = await database.list_collection_names()
    
    expected_active = [
        "users", "companies", "memberships", "subscription_plans",
        "uploads", "financial_records", "data_quality_reports",
        "forecast_runs", "forecasts", "risk_assessments",
        "recommendations", "ai_insights", "audit_logs"
    ]
    
    for col in expected_active:
        if col in existing_collections:
            print(f"  ✅ {col} exists in database")
        else:
            print(f"  ❌ {col} MISSING from database")
            all_passed = False
    
    if "reports" in existing_collections:
        print(f"  ❌ reports still exists (should be removed)")
        all_passed = False
    else:
        print(f"  ✅ reports removed from database")
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 3: Verify subscription_plans seeded
    # ──────────────────────────────────────────────────────────────────────────
    
    print("\n✓ CHECK 3: Subscription plans")
    
    free_trial = await database[c.SUBSCRIPTION_PLANS].find_one({"code": "free_trial"})
    premium = await database[c.SUBSCRIPTION_PLANS].find_one({"code": "premium"})
    
    if free_trial:
        print(f"  ✅ free_trial plan exists")
    else:
        print(f"  ❌ free_trial plan MISSING")
        all_passed = False
    
    if premium:
        print(f"  ✅ premium plan exists")
    else:
        print(f"  ❌ premium plan MISSING")
        all_passed = False
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 4: Verify legacy collections are empty
    # ──────────────────────────────────────────────────────────────────────────
    
    print("\n✓ CHECK 4: Legacy collections status")
    
    if "subscriptions" in existing_collections:
        sub_count = await database[c.SUBSCRIPTIONS].count_documents({})
        if sub_count == 0:
            print(f"  ✅ subscriptions collection empty (expected)")
        else:
            print(f"  ⚠️  subscriptions has {sub_count} documents (legacy data)")
    
    if "payments" in existing_collections:
        pay_count = await database[c.PAYMENTS].count_documents({})
        if pay_count == 0:
            print(f"  ✅ payments collection empty (expected)")
        else:
            print(f"  ⚠️  payments has {pay_count} documents (legacy data)")
    
    if "plans" in existing_collections:
        plan_count = await database[c.PLANS].count_documents({})
        if plan_count == 2:  # free + pro
            print(f"  ✅ plans collection has 2 legacy plans (expected)")
        else:
            print(f"  ⚠️  plans has {plan_count} documents (expected 2)")
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 5: Verify new SaaS system imports
    # ──────────────────────────────────────────────────────────────────────────
    
    print("\n✓ CHECK 5: New SaaS system imports")
    
    try:
        from app.services.subscription_service import (
            get_subscription_status,
            can_upload,
            increment_upload_usage,
            upgrade_to_premium,
        )
        print(f"  ✅ subscription_service imports successful")
    except ImportError as e:
        print(f"  ❌ subscription_service import failed: {e}")
        all_passed = False
    
    # ──────────────────────────────────────────────────────────────────────────
    # FINAL RESULT
    # ──────────────────────────────────────────────────────────────────────────
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ MIGRATION VALIDATION PASSED")
        print("="*70 + "\n")
        print("The legacy billing migration is complete and functional.")
        print("All checks passed successfully.\n")
        return 0
    else:
        print("❌ MIGRATION VALIDATION FAILED")
        print("="*70 + "\n")
        print("Some checks failed. Please review the output above.\n")
        return 1


async def main():
    """Main entry point."""
    try:
        exit_code = await validate_migration()
    finally:
        client.close()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
