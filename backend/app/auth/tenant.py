"""Multi-tenant context from JWT + memberships."""

from fastapi import Depends, HTTPException
from app.utils.bson_utils import ObjectId

from app.auth.dependencies import get_current_user
from app.db import collections as c
from app.db.mongodb import database


async def get_active_company_id(
    current_user: dict = Depends(get_current_user),
) -> str:
    company_id = current_user.get("active_company_id") or current_user.get(
        "company_id"
    )
    if not company_id:
        raise HTTPException(
            status_code=400,
            detail="No active company. Create or select a company first.",
        )
    return str(company_id)


async def get_tenant_context(
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_active_company_id),
) -> dict:
    membership = await database[c.MEMBERSHIPS].find_one(
        {
            "user_id": current_user["_id"],
            "company_id": ObjectId(company_id),
        }
    )
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this company.",
        )

    company = await database[c.COMPANIES].find_one(
        {"_id": ObjectId(company_id)}
    )
    if not company or company.get("status", "active") != "active":
        raise HTTPException(status_code=404, detail="Company not found.")

    return {
        "user": current_user,
        "company_id": company_id,
        "company": company,
        "membership": membership,
        "role": membership.get("role", "viewer"),
    }
