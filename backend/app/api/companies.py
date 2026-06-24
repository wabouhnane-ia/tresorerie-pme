from datetime import datetime, timezone

from app.utils.bson_utils import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.jwt_handler import create_access_token
from app.db import collections as c
from app.db.mongodb import database
from app.schemas.company_schema import CreateCompanySchema
from app.services import audit_service
from app.services.subscription_service import create_trial_subscription

router = APIRouter(prefix="/companies", tags=["Companies"])


def _utcnow():
    return datetime.now(timezone.utc)


@router.post("/create")
async def create_company(
    company: CreateCompanySchema,
    current_user=Depends(get_current_user),
):
    company_doc = {
        "name": company.company_name,
        "company_name": company.company_name,
        "legal_name": company.company_name,
        "sector": company.sector,
        "country": company.country,
        "city": company.city,
        "currency": "MAD",
        "employees_count": company.employees_count,
        "annual_revenue": company.annual_revenue,
        "settings": {
            "timezone": "Africa/Casablanca",
        },
        "status": "active",
        "owner_id": str(current_user["_id"]),
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }

    result = await database[c.COMPANIES].insert_one(company_doc)
    company_id = str(result.inserted_id)

    await database[c.MEMBERSHIPS].insert_one(
        {
            "user_id": current_user["_id"],
            "company_id": result.inserted_id,
            "role": "owner",
            "permissions": ["upload", "forecast", "billing", "admin"],
            "created_at": _utcnow(),
        }
    )

    await create_trial_subscription(company_id)

    await database[c.USERS].update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "active_company_id": company_id,
                "company_id": company_id,
                "updated_at": _utcnow(),
            }
        },
    )

    await audit_service.log_action(
        company_id=company_id,
        user_id=current_user["_id"],
        action="company.create",
        resource_type="company",
        resource_id=company_id,
    )

    token = create_access_token(
        {
            "sub": str(current_user["_id"]),
            "email": current_user["email"],
            "company_id": company_id,
            "role": "owner",
        }
    )

    return {
        "message": "Company created successfully",
        "company_id": company_id,
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_my_company(current_user=Depends(get_current_user)):
    company_id = current_user.get("active_company_id") or current_user.get(
        "company_id"
    )
    if not company_id:
        return {"message": "No company found"}

    company = await database[c.COMPANIES].find_one({"_id": ObjectId(company_id)})
    if not company:
        return {"message": "Company not found"}

    company["_id"] = str(company["_id"])
    
    # LEGACY REMOVED: No longer fetch subscription from separate collection
    # The new SaaS system uses user.subscription embedded field instead
    # Frontend should use GET /billing/usage for subscription info
    
    return company
