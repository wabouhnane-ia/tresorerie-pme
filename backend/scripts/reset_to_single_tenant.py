import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import collections as c

DATA_COLLECTIONS = [
    c.UPLOADS,
    c.FINANCIAL_RECORDS,
    c.COMPANY_TREASURY_PROFILES,
    c.DATA_QUALITY_REPORTS,
    c.FORECAST_RUNS,
    c.FORECASTS,
    c.RECOMMENDATIONS,
    c.RISK_ASSESSMENTS,
    c.AI_INSIGHTS,
    c.TREASURY_PROFILES,
    c.COMPANY_MAPPING_PROFILES,
    c.AUDIT_LOGS,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset the development MongoDB to a single tenant state."
    )
    parser.add_argument(
        "--keep-email",
        dest="keep_email",
        help="Email address of the user to keep. If omitted, the first active user with a membership is selected.",
    )
    parser.add_argument(
        "--keep-company-id",
        dest="keep_company_id",
        help="Company _id to keep. If omitted, company is inferred from the kept user's membership.",
    )
    parser.add_argument(
        "--keep-company-name",
        dest="keep_company_name",
        help="Company name to keep. If omitted, company is inferred from the kept user's membership.",
    )
    parser.add_argument(
        "--full-reset",
        dest="full_reset",
        action="store_true",
        help="Delete all documents from tenant-scoped collections, not just non-selected company documents.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Show what would be deleted without writing changes to the database.",
    )
    return parser.parse_args()


def get_mongo_settings() -> tuple[str, str]:
    env_path = ROOT / ".env"
    load_dotenv(env_path)

    mongodb_url = os.getenv("MONGODB_URL")
    mongodb_db = os.getenv("MONGODB_DB")
    if not mongodb_url or not mongodb_db:
        raise EnvironmentError(
            f"Missing MONGODB_URL or MONGODB_DB in {env_path}."
        )
    return mongodb_url, mongodb_db


def normalize_id(value: str | ObjectId | None) -> ObjectId | None:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(value):
        return ObjectId(value)
    return None


def id_values(value: ObjectId) -> list[ObjectId | str]:
    return [value, str(value)]


async def count_docs(db, collection_name: str, filter_query: dict | None = None) -> int:
    return await db[collection_name].count_documents(filter_query or {})


async def find_keep_user(db, email: str | None) -> dict:
    if email:
        user = await db[c.USERS].find_one({"email": email})
        if user is None:
            raise ValueError(f"No user found for email '{email}'.")
        return user

    membership = await db[c.MEMBERSHIPS].find_one({})
    if membership is None:
        user = await db[c.USERS].find_one({})
        if user is None:
            raise ValueError("Database contains no users.")
        return user

    user = await db[c.USERS].find_one({"_id": membership["user_id"]})
    if user is None:
        raise ValueError("Membership referenced a missing user.")
    return user


async def find_keep_company(db, keep_company_id: str | None, keep_company_name: str | None, keep_user: dict) -> dict:
    if keep_company_id:
        company_id = normalize_id(keep_company_id)
        if company_id is None:
            raise ValueError(f"--keep-company-id '{keep_company_id}' is not a valid ObjectId.")
        company = await db[c.COMPANIES].find_one({"_id": company_id})
        if company is None:
            raise ValueError(f"No company found for _id '{keep_company_id}'.")
        return company

    if keep_company_name:
        company = await db[c.COMPANIES].find_one({"name": keep_company_name})
        if company is None:
            raise ValueError(f"No company found for name '{keep_company_name}'.")
        return company

    membership = await db[c.MEMBERSHIPS].find_one({"user_id": keep_user["_id"]})
    if membership:
        company = await db[c.COMPANIES].find_one({"_id": membership["company_id"]})
        if company is not None:
            return company

    company = await db[c.COMPANIES].find_one({})
    if company is None:
        raise ValueError("Database contains no companies.")
    return company


async def ensure_keep_membership(db, keep_user: dict, keep_company: dict, dry_run: bool) -> bool:
    membership = await db[c.MEMBERSHIPS].find_one(
        {"user_id": keep_user["_id"], "company_id": keep_company["_id"]}
    )
    if membership:
        return False

    if dry_run:
        return True

    await db[c.MEMBERSHIPS].insert_one(
        {
            "user_id": keep_user["_id"],
            "company_id": keep_company["_id"],
            "role": "owner",
            "permissions": ["upload", "forecast", "billing", "admin"],
            "created_at": datetime.utcnow(),
        }
    )
    return True


async def run_cleanup(args: argparse.Namespace) -> None:
    mongodb_url, mongodb_db = get_mongo_settings()
    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]

    args.keep_email = args.keep_email or os.getenv("KEEP_EMAIL")
    args.keep_company_id = args.keep_company_id or os.getenv("KEEP_COMPANY_ID")
    args.keep_company_name = args.keep_company_name or os.getenv("KEEP_COMPANY_NAME")

    keep_user = await find_keep_user(db, args.keep_email)
    keep_company = await find_keep_company(db, args.keep_company_id, args.keep_company_name, keep_user)

    if not args.dry_run:
        await ensure_keep_membership(db, keep_user, keep_company, dry_run=False)
        if keep_user.get("active_company_id") != keep_company["_id"]:
            await db[c.USERS].update_one(
                {"_id": keep_user["_id"]},
                {"$set": {"active_company_id": keep_company["_id"], "updated_at": datetime.utcnow()}},
            )

    company_id_values = id_values(keep_company["_id"])
    membership_keep_filter = {"$and": [{"user_id": keep_user["_id"]}, {"company_id": keep_company["_id"]}]}

    print("=== Single Tenant Reset Configuration ===")
    print(f"Keep user: {keep_user['email']} ({keep_user['_id']})")
    print(f"Keep company: {keep_company['name']} ({keep_company['_id']})")
    print(f"Full reset: {args.full_reset}")
    print(f"Dry run: {args.dry_run}")
    print()

    if args.dry_run:
        print("Dry run mode enabled. No changes will be written to the database.")

    actions = []

    if args.dry_run:
        actions.append((c.USERS, {"_id": {"$ne": keep_user["_id"]}}))
        actions.append((c.COMPANIES, {"_id": {"$ne": keep_company["_id"]}}))
        actions.append((c.MEMBERSHIPS, {"$nor": [membership_keep_filter]}))
        for collection_name in DATA_COLLECTIONS:
            if args.full_reset:
                actions.append((collection_name, {}))
            else:
                actions.append(
                    (
                        collection_name,
                        {
                            "$or": [
                                {"company_id": {"$nin": company_id_values}},
                                {"company_id": {"$exists": False}},
                            ]
                        },
                    )
                )
        for collection_name, filter_query in actions:
            preview_count = await count_docs(db, collection_name, filter_query)
            print(f"Would delete {preview_count} documents from {collection_name}.")
        client.close()
        return

    users_deleted = await db[c.USERS].delete_many({"_id": {"$ne": keep_user["_id"]}})
    companies_deleted = await db[c.COMPANIES].delete_many({"_id": {"$ne": keep_company["_id"]}})
    memberships_deleted = await db[c.MEMBERSHIPS].delete_many({"$nor": [membership_keep_filter]})

    print(f"Deleted {users_deleted.deleted_count} users.")
    print(f"Deleted {companies_deleted.deleted_count} companies.")
    print(f"Deleted {memberships_deleted.deleted_count} memberships.")

    for collection_name in DATA_COLLECTIONS:
        if args.full_reset:
            result = await db[collection_name].delete_many({})
        else:
            result = await db[collection_name].delete_many(
                {
                    "$or": [
                        {"company_id": {"$nin": company_id_values}},
                        {"company_id": {"$exists": False}},
                    ]
                }
            )
        print(f"Deleted {result.deleted_count} documents from {collection_name}.")

    final_counts = {
        collection_name: await count_docs(db, collection_name)
        for collection_name in [c.USERS, c.COMPANIES, c.MEMBERSHIPS] + DATA_COLLECTIONS
    }

    print("\n=== Final counts ===")
    for collection_name, count in final_counts.items():
        print(f"{collection_name}: {count}")

    client.close()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_cleanup(args))
