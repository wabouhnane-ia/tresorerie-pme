from datetime import datetime, timezone

from app.utils.bson_utils import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.jwt_handler import create_access_token
from app.auth.password_handler import hash_password, verify_password
from app.db import collections as c
from app.db.mongodb import database
from app.schemas.auth_schema import LoginSchema, RegisterSchema
from app.schemas.tenant_schema import SelectCompanySchema

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _utcnow():
    return datetime.now(timezone.utc)


@router.post("/register")
async def register_user(user: RegisterSchema):
    existing = await database[c.USERS].find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    doc = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "locale": "fr-MA",
        "is_active": True,
        "email_verified": False,
        "active_company_id": None,
        # ── SaaS foundation ──────────────────────────────────────────────────
        # Every new user starts as owner with a one-time free trial.
        # super_admin is NEVER created via this endpoint.
        "role": "owner",
        "subscription": {
            "plan_code": "free_trial",
            "started_at": _utcnow().isoformat(),
        },
        "usage": {
            "total_uploads": 0,
            "total_forecast_runs": 0,
        },
        # ─────────────────────────────────────────────────────────────────────
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }
    result = await database[c.USERS].insert_one(doc)
    return {"message": "User created successfully", "user_id": str(result.inserted_id)}


@router.post("/login")
async def login_user(user: LoginSchema):
    db_user = await database[c.USERS].find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await database[c.USERS].update_one(
        {"_id": db_user["_id"]},
        {"$set": {"last_login_at": _utcnow()}},
    )

    companies = await _list_user_companies(db_user["_id"])
    active_id = db_user.get("active_company_id") or db_user.get("company_id")

    token_data = {
        "sub": str(db_user["_id"]),
        "email": db_user["email"],
    }
    if active_id:
        token_data["company_id"] = str(active_id)

    return {
        "access_token": create_access_token(token_data),
        "token_type": "bearer",
        "user_id": str(db_user["_id"]),
        "active_company_id": str(active_id) if active_id else None,
        "companies": companies,
    }


@router.post("/select-company")
async def select_company(
    body: SelectCompanySchema,
    current_user=Depends(get_current_user),
):
    membership = await database[c.MEMBERSHIPS].find_one(
        {
            "user_id": current_user["_id"],
            "company_id": ObjectId(body.company_id),
        }
    )
    if not membership:
        raise HTTPException(status_code=403, detail="No access to this company")

    await database[c.USERS].update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "active_company_id": body.company_id,
                "company_id": body.company_id,
                "updated_at": _utcnow(),
            }
        },
    )

    token = create_access_token(
        {
            "sub": str(current_user["_id"]),
            "email": current_user["email"],
            "company_id": body.company_id,
            "role": membership.get("role", "viewer"),
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "company_id": body.company_id,
        "role": membership.get("role"),
    }


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    companies = await _list_user_companies(current_user["_id"])
    return {
        "user_id": str(current_user["_id"]),
        "email": current_user["email"],
        "first_name": current_user.get("first_name"),
        "last_name": current_user.get("last_name"),
        "active_company_id": current_user.get("active_company_id")
        or current_user.get("company_id"),
        "companies": companies,
        # SaaS fields
        "role": current_user.get("role", "owner"),
        "subscription": current_user.get("subscription"),
        "usage": current_user.get("usage", {"total_uploads": 0, "total_forecast_runs": 0}),
    }


async def _list_user_companies(user_id: ObjectId) -> list[dict]:
    cursor = database[c.MEMBERSHIPS].find({"user_id": user_id})
    items = []
    async for m in cursor:
        company = await database[c.COMPANIES].find_one({"_id": m["company_id"]})
        if company:
            items.append(
                {
                    "company_id": str(company["_id"]),
                    "name": company.get("name") or company.get("company_name"),
                    "role": m.get("role"),
                    "sector": company.get("sector"),
                }
            )
    return items
