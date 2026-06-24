from datetime import (
    datetime,
    timedelta
)

from jose import jwt, JWTError

from app.core.config import settings


def create_access_token(

    data: dict
):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(

        minutes=
        settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({

        "exp": expire
    })

    encoded_jwt = jwt.encode(

        to_encode,

        settings.JWT_SECRET_KEY,

        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise ValueError("Invalid token")