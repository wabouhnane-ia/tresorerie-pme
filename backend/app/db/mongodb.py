from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL)
database = client[settings.MONGODB_DB]


async def close_mongo_connection() -> None:
    client.close()


async def ping_mongo() -> bool:
    """Ping MongoDB; return False on error instead of raising to allow
    the application to start in development environments where Atlas
    connectivity or TLS issues may occur.
    """
    try:
        await client.admin.command("ping")
        return True
    except Exception as e:
        # Log minimal info and return False so startup continues.
        # In production you may want to re-raise or fail hard.
        print(f"Warning: ping_mongo failed: {e}")
        return False
