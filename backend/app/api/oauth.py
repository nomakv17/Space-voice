"""OAuth routes for Google Calendar and Calendly integrations."""

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, user_id_to_uuid
from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user_integration import UserIntegration

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])
logger = structlog.get_logger()

# OAuth state TTL (10 minutes)
OAUTH_STATE_TTL = 600


# =============================================================================
# Google Calendar OAuth
# =============================================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


@router.get("/google-calendar/connect")
async def google_calendar_connect(
    request: Request,
    current_user: CurrentUser,
    workspace_id: str | None = Query(default=None),
) -> dict[str, str]:
    """Initiate Google Calendar OAuth flow.

    Returns the authorization URL that the frontend should redirect to.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google Calendar integration not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in Redis with user context
    redis = await get_redis()
    state_data = {
        "user_id": current_user.id,
        "workspace_id": workspace_id,
        "provider": "google-calendar",
    }
    await redis.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, str(state_data))

    # Build authorization URL
    redirect_uri = f"{settings.PUBLIC_URL}/api/v1/oauth/google-calendar/callback"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent to get refresh token
        "state": state,
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    logger.info("google_calendar_oauth_initiated", user_id=current_user.id)

    return {"auth_url": auth_url}


@router.get("/google-calendar/callback")
async def google_calendar_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Google Calendar OAuth callback."""
    # Check for OAuth error
    if error:
        logger.warning("google_calendar_oauth_error", error=error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/integrations?error={error}"
        )

    # Verify state
    redis = await get_redis()
    state_data_str = await redis.get(f"oauth_state:{state}")
    if not state_data_str:
        logger.warning("google_calendar_invalid_state")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/integrations?error=invalid_state"
        )

    # Parse state data
    state_data = eval(state_data_str)  # Safe since we created it
    user_id = state_data["user_id"]
    workspace_id = state_data.get("workspace_id")

    # Delete used state
    await redis.delete(f"oauth_state:{state}")

    # Exchange code for tokens
    redirect_uri = f"{settings.PUBLIC_URL}/api/v1/oauth/google-calendar/callback"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                logger.error("google_calendar_token_error", response=response.text)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/dashboard/integrations?error=token_exchange_failed"
                )

            tokens = response.json()
    except Exception as e:
        logger.exception("google_calendar_token_exception", error=str(e))
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/integrations?error=token_exchange_failed"
        )

    # Store integration
    user_uuid = user_id_to_uuid(user_id)
    workspace_uuid = uuid.UUID(workspace_id) if workspace_id else None

    # Check if integration already exists
    conditions = [
        UserIntegration.user_id == user_uuid,
        UserIntegration.integration_id == "google-calendar",
    ]
    if workspace_uuid:
        conditions.append(UserIntegration.workspace_id == workspace_uuid)
    else:
        conditions.append(UserIntegration.workspace_id.is_(None))

    result = await db.execute(select(UserIntegration).where(and_(*conditions)))
    existing = result.scalar_one_or_none()

    credentials = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"),
        "expires_in": tokens.get("expires_in"),
        "scope": tokens.get("scope"),
    }

    if existing:
        # Update existing integration
        existing.credentials = credentials
        existing.is_active = True
        existing.updated_at = datetime.now(UTC)
    else:
        # Create new integration
        integration = UserIntegration(
            user_id=user_uuid,
            workspace_id=workspace_uuid,
            integration_id="google-calendar",
            integration_name="Google Calendar",
            credentials=credentials,
            is_active=True,
        )
        db.add(integration)

    await db.commit()

    logger.info("google_calendar_connected", user_id=user_id)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard/integrations?success=google-calendar"
    )


# =============================================================================
# Calendly OAuth
# =============================================================================

CALENDLY_AUTH_URL = "https://auth.calendly.com/oauth/authorize"
CALENDLY_TOKEN_URL = "https://auth.calendly.com/oauth/token"


@router.get("/calendly/connect")
async def calendly_connect(
    request: Request,
    current_user: CurrentUser,
    workspace_id: str | None = Query(default=None),
) -> dict[str, str]:
    """Initiate Calendly OAuth flow."""
    if not settings.CALENDLY_CLIENT_ID or not settings.CALENDLY_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Calendly integration not configured. Please set CALENDLY_CLIENT_ID and CALENDLY_CLIENT_SECRET.",
        )

    # Generate state token
    state = secrets.token_urlsafe(32)

    # Store state in Redis
    redis = await get_redis()
    state_data = {
        "user_id": current_user.id,
        "workspace_id": workspace_id,
        "provider": "calendly",
    }
    await redis.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, str(state_data))

    # Build authorization URL
    redirect_uri = f"{settings.PUBLIC_URL}/api/v1/oauth/calendly/callback"
    params = {
        "client_id": settings.CALENDLY_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    }

    auth_url = f"{CALENDLY_AUTH_URL}?{urlencode(params)}"

    logger.info("calendly_oauth_initiated", user_id=current_user.id)

    return {"auth_url": auth_url}


@router.get("/calendly/callback")
async def calendly_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Calendly OAuth callback."""
    if error:
        logger.warning("calendly_oauth_error", error=error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/integrations?error={error}"
        )

    # Verify state
    redis = await get_redis()
    state_data_str = await redis.get(f"oauth_state:{state}")
    if not state_data_str:
        logger.warning("calendly_invalid_state")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/integrations?error=invalid_state"
        )

    state_data = eval(state_data_str)
    user_id = state_data["user_id"]
    workspace_id = state_data.get("workspace_id")

    await redis.delete(f"oauth_state:{state}")

    # Exchange code for tokens
    redirect_uri = f"{settings.PUBLIC_URL}/api/v1/oauth/calendly/callback"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CALENDLY_TOKEN_URL,
                data={
                    "client_id": settings.CALENDLY_CLIENT_ID,
                    "client_secret": settings.CALENDLY_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error("calendly_token_error", response=response.text)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/dashboard/integrations?error=token_exchange_failed"
                )

            tokens = response.json()
    except Exception as e:
        logger.exception("calendly_token_exception", error=str(e))
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard/integrations?error=token_exchange_failed"
        )

    # Get user info to get organization URI
    try:
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://api.calendly.com/users/me",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            if user_response.status_code == 200:
                user_info = user_response.json()
                organization_uri = user_info.get("resource", {}).get("current_organization")
            else:
                organization_uri = None
    except Exception:
        organization_uri = None

    # Store integration
    user_uuid = user_id_to_uuid(user_id)
    workspace_uuid = uuid.UUID(workspace_id) if workspace_id else None

    conditions = [
        UserIntegration.user_id == user_uuid,
        UserIntegration.integration_id == "calendly",
    ]
    if workspace_uuid:
        conditions.append(UserIntegration.workspace_id == workspace_uuid)
    else:
        conditions.append(UserIntegration.workspace_id.is_(None))

    result = await db.execute(select(UserIntegration).where(and_(*conditions)))
    existing = result.scalar_one_or_none()

    credentials = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"),
        "expires_in": tokens.get("expires_in"),
        "organization_uri": organization_uri,
    }

    if existing:
        existing.credentials = credentials
        existing.is_active = True
        existing.updated_at = datetime.now(UTC)
    else:
        integration = UserIntegration(
            user_id=user_uuid,
            workspace_id=workspace_uuid,
            integration_id="calendly",
            integration_name="Calendly",
            credentials=credentials,
            is_active=True,
        )
        db.add(integration)

    await db.commit()

    logger.info("calendly_connected", user_id=user_id)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard/integrations?success=calendly"
    )


# =============================================================================
# Token Refresh Utilities
# =============================================================================


async def refresh_google_token(credentials: dict[str, Any]) -> dict[str, Any] | None:
    """Refresh Google OAuth token."""
    refresh_token = credentials.get("refresh_token")
    if not refresh_token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 200:
                new_tokens = response.json()
                return {
                    "access_token": new_tokens["access_token"],
                    "refresh_token": refresh_token,  # Keep original refresh token
                    "token_type": new_tokens.get("token_type", "Bearer"),
                    "expires_in": new_tokens.get("expires_in"),
                }
    except Exception as e:
        logger.exception("google_token_refresh_failed", error=str(e))

    return None


async def refresh_calendly_token(credentials: dict[str, Any]) -> dict[str, Any] | None:
    """Refresh Calendly OAuth token."""
    refresh_token = credentials.get("refresh_token")
    if not refresh_token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CALENDLY_TOKEN_URL,
                data={
                    "client_id": settings.CALENDLY_CLIENT_ID,
                    "client_secret": settings.CALENDLY_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                new_tokens = response.json()
                return {
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens.get("refresh_token", refresh_token),
                    "token_type": new_tokens.get("token_type", "Bearer"),
                    "expires_in": new_tokens.get("expires_in"),
                    "organization_uri": credentials.get("organization_uri"),
                }
    except Exception as e:
        logger.exception("calendly_token_refresh_failed", error=str(e))

    return None
