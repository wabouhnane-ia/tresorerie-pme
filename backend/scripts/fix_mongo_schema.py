import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()


async def fix():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db = os.getenv("MONGODB_DB", "tresorerie_ai")
    
    print(f"Connecting to MongoDB: {mongodb_url}")
    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]
    
    print("\nRemoving JSON schema validator from forecast_runs...")
    try:
        await db.command({
            "collMod": "forecast_runs",
            "validator": {},
            "validationLevel": "off"
        })
        print("✅ forecast_runs validator removed")
    except Exception as e:
        print(f"⚠️  Warning: Could not remove validator (may not exist): {e}")
    
    print("\nRemoving scenario field from all documents...")
    collections = [
        "forecast_runs",
        "forecasts",
        "financial_records",
        "ai_insights",
        "risk_assessments",
        "uploads"
    ]
    
    for col_name in collections:
        try:
            result = await db[col_name].update_many(
                {"scenario": {"$exists": True}},
                {"$unset": {"scenario": ""}}
            )
            print(f"✅ {col_name}: {result.modified_count} documents cleaned")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean {col_name}: {e}")
    
    client.close()
    print("\n✅ MongoDB schema fix completed!")


if __name__ == "__main__":
    asyncio.run(fix())
