from fastapi import (
    Depends,
    HTTPException
)

from fastapi.security import (
    OAuth2PasswordBearer
)

from jose import jwt

from app.utils.bson_utils import ObjectId

from app.core.config import settings

from app.db import collections as c
from app.db.mongodb import database


oauth2_scheme = OAuth2PasswordBearer(

    tokenUrl="/auth/login"
)


async def get_current_user(

    token: str = Depends(
        oauth2_scheme
    )
):

    try:

        payload = jwt.decode(

            token,

            settings.JWT_SECRET_KEY,

            algorithms=[
                settings.JWT_ALGORITHM
            ]
        )

        user_id = payload.get("sub")

        if not user_id:

            raise HTTPException(

                status_code=401,

                detail="Invalid token"
            )

        user = await database[c.USERS].find_one({

            "_id": ObjectId(user_id)
        })

        if not user:

            raise HTTPException(

                status_code=401,

                detail="User not found"
            )

        company_id = payload.get("company_id")
        if company_id:
            user["active_company_id"] = company_id

        return user

    except Exception:

        raise HTTPException(

            status_code=401,

            detail="Invalid token"
        )