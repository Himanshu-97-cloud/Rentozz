
import uuid
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.profile import Profile


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")

    return PyJWKClient(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    )


def verify_supabase_token(token: str) -> dict[str, Any]:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured.",
        )

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
            options={"require": ["exp", "sub", "iss", "aud"]},
        )

    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
        ) from exc


def get_current_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Profile:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer access token required.",
        )

    claims = verify_supabase_token(credentials.credentials)

    try:
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid user identity in access token.",
        ) from exc

    profile = db.get(Profile, user_id)

    if profile is not None:
        return profile

    metadata = claims.get("user_metadata") or {}
    phone = claims.get("phone") or None
    email = claims.get("email") or None
    full_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or ""
    ).strip() or None

    profile = Profile(
        id=user_id,
        phone=phone,
        email=email,
        full_name=full_name,
        role="renter",
    )

    try:
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    except IntegrityError as exc:
        db.rollback()

        # Another request may have created this profile concurrently.
        existing_profile = db.get(Profile, user_id)
        if existing_profile is not None:
            return existing_profile

        # Avoid returning a database error for duplicate empty phone values.
        raise HTTPException(
            status_code=409,
            detail=(
                "Could not create profile because a phone number or email "
                "is already associated with another profile."
            ),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create user profile.",
        ) from exc


def require_roles(*allowed_roles: str):
    valid_roles = {"renter", "rental_partner", "admin"}

    if not allowed_roles or not set(allowed_roles).issubset(valid_roles):
        raise ValueError("Invalid or missing role configuration.")

    def dependency(
        profile: Profile = Depends(get_current_profile),
    ) -> Profile:
        if profile.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action.",
            )
        return profile

    return dependency
