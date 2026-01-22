"""Onboarding API routes for new user setup."""


import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.session import get_db
from app.models.user_settings import UserSettings
from app.models.workspace import Workspace

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])
logger = structlog.get_logger()


# =============================================================================
# Pydantic Models
# =============================================================================


class OnboardingStatusResponse(BaseModel):
    """Onboarding status response."""

    onboarding_completed: bool
    onboarding_step: int
    company_name: str | None = None
    company_size: str | None = None
    industry: str | None = None
    phone_number: str | None = None
    has_workspace: bool = False
    has_telephony: bool = False
    use_platform_ai: bool = True
    has_ai_config: bool = False


class ProfileUpdateRequest(BaseModel):
    """Profile update request for onboarding step 1."""

    full_name: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    company_size: str = Field(..., pattern="^(solo|2-10|11-50|51-200|200\\+)$")
    industry: str = Field(..., min_length=1, max_length=100)
    phone_number: str | None = Field(None, max_length=50)


class TelephonyConfigRequest(BaseModel):
    """Telephony configuration request for onboarding step 2."""

    provider: str = Field(..., pattern="^(telnyx|twilio)$")
    # Telnyx fields
    telnyx_api_key: str | None = None
    telnyx_public_key: str | None = None
    # Twilio fields
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None


class AIConfigRequest(BaseModel):
    """AI configuration request for onboarding step 3."""

    use_platform_ai: bool = True
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation request for onboarding step 4."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class OnboardingCompleteRequest(BaseModel):
    """Request to mark onboarding as complete."""



# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Get current onboarding status for the user."""
    # Check if user has any workspaces
    result = await db.execute(
        select(Workspace).where(Workspace.user_id == current_user.id).limit(1)
    )
    has_workspace = result.scalar_one_or_none() is not None

    # Check if user has telephony configured (via user_settings)
    settings_result = await db.execute(
        select(UserSettings).where(
            UserSettings.user_id == current_user.id,
            UserSettings.workspace_id.is_(None),  # User-level settings
        ).limit(1)
    )
    user_settings = settings_result.scalar_one_or_none()

    # Determine if telephony is configured (has Telnyx or Twilio credentials)
    has_telephony = False
    has_ai_config = False
    if user_settings:
        has_telephony = bool(
            user_settings.telnyx_api_key or user_settings.twilio_account_sid
        )
        has_ai_config = bool(
            user_settings.openai_api_key or user_settings.deepgram_api_key
        )

    # If using platform AI, AI config is always considered "set up"
    if current_user.use_platform_ai:
        has_ai_config = True

    return OnboardingStatusResponse(
        onboarding_completed=current_user.onboarding_completed,
        onboarding_step=current_user.onboarding_step,
        company_name=current_user.company_name,
        company_size=current_user.company_size,
        industry=current_user.industry,
        phone_number=current_user.phone_number,
        has_workspace=has_workspace,
        has_telephony=has_telephony,
        use_platform_ai=current_user.use_platform_ai,
        has_ai_config=has_ai_config,
    )


@router.post("/profile", response_model=OnboardingStatusResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Update user profile during onboarding (step 1)."""
    log = logger.bind(user_id=current_user.id)
    log.info("updating_onboarding_profile", company=request.company_name)

    # Update user profile
    current_user.full_name = request.full_name
    current_user.company_name = request.company_name
    current_user.company_size = request.company_size
    current_user.industry = request.industry
    current_user.phone_number = request.phone_number

    # Advance to step 2 if still on step 1
    if current_user.onboarding_step == 1:
        current_user.onboarding_step = 2

    await db.commit()
    await db.refresh(current_user)

    log.info("onboarding_profile_updated", step=current_user.onboarding_step)

    return await get_onboarding_status(current_user, db)


@router.post("/telephony", response_model=OnboardingStatusResponse)
async def configure_telephony(
    request: TelephonyConfigRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Configure telephony provider during onboarding (step 2).

    Note: In production, store these credentials securely in user_settings table.
    For this implementation, we validate the provider and advance the step.
    """
    log = logger.bind(user_id=current_user.id, provider=request.provider)
    log.info("configuring_telephony")

    # Validate required fields based on provider
    if request.provider == "telnyx":
        if not request.telnyx_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telnyx API key is required",
            )
    elif request.provider == "twilio":
        if not request.twilio_account_sid or not request.twilio_auth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Twilio Account SID and Auth Token are required",
            )

    # TODO: Store credentials securely in user_settings table
    # For now, we just advance the onboarding step

    # Advance to step 3 if on step 2
    if current_user.onboarding_step == 2:
        current_user.onboarding_step = 3

    await db.commit()
    await db.refresh(current_user)

    log.info("telephony_configured", step=current_user.onboarding_step)

    return await get_onboarding_status(current_user, db)


@router.post("/ai-config", response_model=OnboardingStatusResponse)
async def configure_ai(
    request: AIConfigRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Configure AI provider during onboarding (step 3 - optional)."""
    log = logger.bind(user_id=current_user.id, use_platform=request.use_platform_ai)
    log.info("configuring_ai")

    # Save the AI configuration choice
    current_user.use_platform_ai = request.use_platform_ai

    # If bringing own keys, store them in UserSettings
    if not request.use_platform_ai and (request.openai_api_key or request.anthropic_api_key):
        # Get or create user settings
        settings_result = await db.execute(
            select(UserSettings).where(
                UserSettings.user_id == current_user.id,
                UserSettings.workspace_id.is_(None),
            ).limit(1)
        )
        user_settings = settings_result.scalar_one_or_none()

        if not user_settings:
            user_settings = UserSettings(user_id=current_user.id)
            db.add(user_settings)

        if request.openai_api_key:
            user_settings.openai_api_key = request.openai_api_key
        # Note: anthropic_api_key would need to be added to UserSettings model if needed

    # Advance to step 4 if on step 3
    if current_user.onboarding_step == 3:
        current_user.onboarding_step = 4

    await db.commit()
    await db.refresh(current_user)

    log.info("ai_configured", step=current_user.onboarding_step, use_platform=request.use_platform_ai)

    return await get_onboarding_status(current_user, db)


@router.post("/workspace", response_model=OnboardingStatusResponse)
async def create_first_workspace(
    request: WorkspaceCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Create first workspace during onboarding (step 4)."""
    log = logger.bind(user_id=current_user.id, workspace_name=request.name)
    log.info("creating_first_workspace")

    # Check if user already has a workspace
    result = await db.execute(
        select(Workspace).where(Workspace.user_id == current_user.id).limit(1)
    )
    existing = result.scalar_one_or_none()

    if existing:
        log.info("workspace_already_exists", workspace_id=str(existing.id))
    else:
        # Create the workspace
        workspace = Workspace(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            is_default=True,
        )
        db.add(workspace)
        await db.flush()
        log.info("workspace_created", workspace_id=str(workspace.id))

    # Advance to step 5 if on step 4
    if current_user.onboarding_step == 4:
        current_user.onboarding_step = 5

    await db.commit()
    await db.refresh(current_user)

    return await get_onboarding_status(current_user, db)


@router.post("/complete", response_model=OnboardingStatusResponse)
async def complete_onboarding(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Mark onboarding as complete."""
    log = logger.bind(user_id=current_user.id)
    log.info("completing_onboarding")

    current_user.onboarding_completed = True

    await db.commit()
    await db.refresh(current_user)

    log.info("onboarding_completed")

    return await get_onboarding_status(current_user, db)


@router.post("/skip-step", response_model=OnboardingStatusResponse)
async def skip_current_step(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Skip the current onboarding step (for optional steps like AI config)."""
    log = logger.bind(user_id=current_user.id, current_step=current_user.onboarding_step)

    # Only allow skipping steps 2-4 (telephony, AI, workspace can be done later)
    if current_user.onboarding_step < 2 or current_user.onboarding_step > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This step cannot be skipped",
        )

    current_user.onboarding_step += 1
    log.info("step_skipped", new_step=current_user.onboarding_step)

    await db.commit()
    await db.refresh(current_user)

    return await get_onboarding_status(current_user, db)
