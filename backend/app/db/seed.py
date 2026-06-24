"""Seed subscription plan catalog (idempotent).



Sprint 9: single commercial plan — Intelligence Trésorerie PME.

"""



from datetime import datetime, timezone



from app.db import collections as c

from app.db.mongodb import database





def _utcnow():

    return datetime.now(timezone.utc)





SUBSCRIPTION_PLAN = {

    "code": "intelligence_tresorerie_pme",

    "name": "Intelligence Trésorerie PME",

    "description": "Plateforme complète de gestion et d'intelligence de trésorerie pour PME",

    "billing_period": "monthly",

    "price_mad": 299.0,

    "currency": "MAD",

    "trial_days": 14,

    "features": [

        "upload_intelligent",

        "memoire_historique",

        "previsions",

        "business_intelligence",

        "decision_center",

        "notifications",

        "executive_pdf",

    ],

    "is_active": True,

}





async def seed_plans() -> None:

    """Idempotent seed for the single SaaS plan."""

    await database[c.SUBSCRIPTION_PLANS].update_one(

        {"code": SUBSCRIPTION_PLAN["code"]},

        {

            "$set": {**SUBSCRIPTION_PLAN, "updated_at": _utcnow()},

            "$setOnInsert": {"created_at": _utcnow()},

        },

        upsert=True,

    )



    # Deprecate legacy multi-plan codes (keep documents but mark inactive)

    for legacy_code in ("free_trial", "premium", "treasury_intelligence_pro"):

        await database[c.SUBSCRIPTION_PLANS].update_one(

            {"code": legacy_code},

            {"$set": {"is_active": False, "updated_at": _utcnow()}},

        )


