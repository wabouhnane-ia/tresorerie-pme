"""
reset_db.py — Complete database reset and initialization.

Usage:
    cd backend
    python -m scripts.reset_db

What this script does:
  1. Drops all existing collections
  2. Creates all required collections
  3. Creates all indexes
  4. Seeds subscription plans (free_trial + premium)
  5. Creates the default super_admin user if not already present

Super admin rules:
  - role: "super_admin"
  - subscription: null  (no plan required — bypasses everything)
  - usage: null         (no tracking)
  - NEVER created via /auth/register
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from the backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.password_handler import hash_password
from app.db import collections as c
from app.db.mongodb import client, database
from app.db.init_indexes import init_indexes
from app.db.seed import seed_plans

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

SUPER_ADMIN_EMAIL = "admin@treasury-ai.com"
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "Admin@TreasuryAI2025!")

# All collections that should exist
ALL_COLLECTIONS = [
    c.USERS,
    c.COMPANIES,
    c.MEMBERSHIPS,
    c.SUBSCRIPTION_PLANS,
    c.PLANS,  # LEGACY - TO REMOVE AFTER MIGRATION
    c.SUBSCRIPTIONS,  # LEGACY - TO REMOVE AFTER MIGRATION
    c.PAYMENTS,  # LEGACY - TO REMOVE AFTER MIGRATION
    c.UPLOADS,
    c.FINANCIAL_RECORDS,
    c.DATA_QUALITY_REPORTS,
    c.FORECAST_RUNS,
    c.FORECASTS,
    c.RISK_ASSESSMENTS,
    c.RECOMMENDATIONS,
    c.AI_INSIGHTS,
    c.AUDIT_LOGS,
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# Database reset
# ──────────────────────────────────────────────────────────────────────────────

async def drop_all_collections() -> None:
    """Drop all existing collections."""
    existing_collections = await database.list_collection_names()
    
    for collection_name in existing_collections:
        await database.drop_collection(collection_name)
        print(f"   ✅ Dropped collection: {collection_name}")
    
    if existing_collections:
        print(f"   🗑️  Dropped {len(existing_collections)} collections")
    else:
        print("   ℹ️  No existing collections to drop")


async def create_all_collections() -> None:
    """Create all required collections."""
    for collection_name in ALL_COLLECTIONS:
        await database.create_collection(collection_name)
        print(f"   ✅ Created collection: {collection_name}")
    
    print(f"   📦 Created {len(ALL_COLLECTIONS)} collections")


# ──────────────────────────────────────────────────────────────────────────────
# Super admin creation
# ──────────────────────────────────────────────────────────────────────────────

async def create_super_admin() -> None:
    """
    Creates the default super_admin user (idempotent).

    Super admin:
      - role: "super_admin"
      - subscription: null   ← intentional, bypasses all billing
      - usage: null          ← no tracking needed
    """
    existing = await database[c.USERS].find_one({"email": SUPER_ADMIN_EMAIL})

    if existing:
        # Ensure the existing user has the correct super_admin fields
        await database[c.USERS].update_one(
            {"email": SUPER_ADMIN_EMAIL},
            {
                "$set": {
                    "role": "super_admin",
                    "subscription": None,
                    "usage": None,
                    "is_active": True,
                    "updated_at": _utcnow(),
                }
            },
        )
        print(f"   ✅ Super admin already exists — fields refreshed: {SUPER_ADMIN_EMAIL}")
        return

    doc = {
        "first_name": "Super",
        "last_name": "Admin",
        "email": SUPER_ADMIN_EMAIL,
        "password_hash": hash_password(SUPER_ADMIN_PASSWORD),
        "locale": "fr-MA",
        "is_active": True,
        "email_verified": True,
        "active_company_id": None,
        # ── SaaS: super_admin has NO subscription and NO usage tracking ──────
        "role": "super_admin",
        "subscription": None,   # intentional null — bypasses all billing
        "usage": None,          # intentional null — no quota tracking
        # ─────────────────────────────────────────────────────────────────────
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }

    await database[c.USERS].insert_one(doc)
    print(f"   ✅ Super admin created: {SUPER_ADMIN_EMAIL}")
    print(f"   🔑 Password: {SUPER_ADMIN_PASSWORD}")
    print("   ⚠️  Change this password in production!")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n🚀 Starting complete database reset and initialization...\n")

    # 1. Drop all collections
    print("🗑️  Dropping all existing collections...")
    await drop_all_collections()

    # 2. Create all collections
    print("\n📦 Creating all required collections...")
    await create_all_collections()

    # 3. Create indexes
    print("\n🔍 Creating indexes...")
    await init_indexes()

    # 4. Seed plans
    print("\n📋 Seeding subscription plans...")
    await seed_plans()
    print("   ✅ subscription_plans seeded (free_trial + premium)")
    print("   ✅ legacy plans seeded (free + pro)")

    # 5. Create super admin
    print("\n👤 Creating super admin...")
    await create_super_admin()

    # 6. Close connection
    client.close()
    print("\n✅ Database reset and initialization complete.\n")
    print("📊 Summary:")
    print(f"   • Collections: {len(ALL_COLLECTIONS)}")
    print("   • Indexes: Created for all collections")
    print("   • Plans: 4 plans seeded (2 new + 2 legacy)")
    print("   • Super admin: Ready")
    print("\n🎯 Database is ready for use!")


if __name__ == "__main__":
    asyncio.run(main())
