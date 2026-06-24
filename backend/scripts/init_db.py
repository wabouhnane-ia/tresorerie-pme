"""Initialize MongoDB indexes and seed plans.

Usage (from backend/):
    python -m scripts.init_db
"""

import asyncio

from app.db.init_indexes import init_indexes
from app.db.mongodb import close_mongo_connection, ping_mongo
from app.db.seed import seed_plans


async def main():
    await ping_mongo()
    print("MongoDB connection OK")
    await init_indexes()
    print("Indexes created")
    await seed_plans()
    print("Plans seeded")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
