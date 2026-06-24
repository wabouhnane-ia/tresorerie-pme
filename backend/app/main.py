from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.subscription import router as subscription_router
from app.api.companies import router as companies_router
from app.api.admin import router as admin_router
from app.api.dashboard import router as dashboard_router
from app.api.decisions import router as decisions_router
from app.api.forecast_routes import router as forecast_router
from app.api.notifications import router as notifications_router
from app.api.upload import router as upload_router
from app.core.config import settings
from app.db.init_indexes import init_indexes
from app.db.mongodb import close_mongo_connection, ping_mongo
from app.db.seed import seed_plans


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ping_mongo()
    await init_indexes()
    await seed_plans()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(upload_router)
app.include_router(analytics_router)
app.include_router(decisions_router)
app.include_router(notifications_router)
app.include_router(forecast_router)
app.include_router(billing_router)
app.include_router(subscription_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    mongo_ok = await ping_mongo()
    return {
        "status": "healthy" if mongo_ok else "degraded",
        "api": settings.APP_NAME,
        "mongodb": mongo_ok,
    }
