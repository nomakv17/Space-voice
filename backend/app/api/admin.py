"""Admin API routes for managing clients, pricing, and access tokens."""

import secrets
import string
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_password_hash
from app.core.auth import CurrentUser, require_write_access
from app.core.config import settings
from app.db.session import get_db
from app.models.access_token import AccessToken
from app.models.pricing_config import PricingConfig
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = structlog.get_logger()


def generate_client_id() -> str:
    """Generate a unique client ID like 'SV-A1B2C3'."""
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(6))
    return f"SV-{random_part}"


# =============================================================================
# Pydantic Models
# =============================================================================


class CreateClientRequest(BaseModel):
    """Request to create a new client."""

    email: str = Field(default="", max_length=255)  # Optional, collected during onboarding
    username: str = Field(default="", max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class ClientResponse(BaseModel):
    """Client response."""

    id: int
    client_id: str | None = None
    email: str
    username: str | None = None
    onboarding_completed: bool
    onboarding_step: int
    company_name: str | None = None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: User) -> "ClientResponse":
        """Create response from User model."""
        return cls(
            id=user.id,
            client_id=user.client_id,
            email=user.email,
            username=user.full_name,
            onboarding_completed=user.onboarding_completed,
            onboarding_step=user.onboarding_step,
            company_name=user.company_name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )


# =============================================================================
# Helper Functions
# =============================================================================


def require_admin(current_user: CurrentUser) -> User:
    """Require the current user to be an admin (read-only allowed)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_admin_write(current_user: CurrentUser) -> User:
    """Require admin access AND write permissions.

    Use this for POST, PUT, DELETE operations that modify data.
    """
    require_admin(current_user)
    require_write_access(current_user)
    return current_user


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ClientResponse]:
    """List all client accounts (non-admin users)."""
    require_admin(current_user)

    result = await db.execute(
        select(User)
        .where(User.is_superuser == False)  # noqa: E712
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [ClientResponse.from_user(user) for user in users]


@router.post("/clients", response_model=ClientResponse)
async def create_client(
    body: CreateClientRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    """Create a new client account with a unique Client ID."""
    require_admin_write(current_user)

    # Generate unique client_id
    client_id = generate_client_id()
    while True:
        result = await db.execute(select(User).where(User.client_id == client_id))
        if not result.scalar_one_or_none():
            break
        client_id = generate_client_id()

    log = logger.bind(admin_id=current_user.id, client_id=client_id)
    log.info("creating_client")

    # Check if email already exists (if provided)
    if body.email:
        result = await db.execute(select(User).where(User.email == body.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        email = body.email
    else:
        # Generate placeholder email using client_id
        email = f"{client_id.lower()}@client.spacevoice.ai"

    # Create client user (NOT superuser, NOT onboarding completed)
    client = User(
        email=email,
        client_id=client_id,
        full_name=body.username or None,
        hashed_password=get_password_hash(body.password),
        is_active=True,
        is_superuser=False,
        onboarding_completed=False,
        onboarding_step=1,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)

    log.info("client_created", db_id=client.id)
    return ClientResponse.from_user(client)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    """Get a specific client by ID."""
    require_admin(current_user)

    result = await db.execute(
        select(User).where(User.id == client_id, User.is_superuser == False)  # noqa: E712
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return ClientResponse.from_user(client)


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a client account."""
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id, client_id=client_id)

    result = await db.execute(
        select(User).where(User.id == client_id, User.is_superuser == False)  # noqa: E712
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    await db.delete(client)
    await db.commit()

    log.info("client_deleted")
    return {"message": "Client deleted successfully"}


# =============================================================================
# Pricing Pydantic Models
# =============================================================================


class PricingConfigResponse(BaseModel):
    """Pricing configuration response."""

    id: int
    tier_id: str
    tier_name: str
    description: str | None = None

    # Base costs (what SpaceVoice pays)
    base_llm_cost_per_minute: float
    base_stt_cost_per_minute: float
    base_tts_cost_per_minute: float
    base_telephony_cost_per_minute: float
    total_base_cost_per_minute: float

    # Markups
    ai_markup_percentage: float
    telephony_markup_percentage: float

    # Final prices (what clients pay)
    final_ai_price_per_minute: float
    final_telephony_price_per_minute: float
    final_total_price_per_minute: float

    # Computed profit metrics
    profit_per_minute: float
    profit_margin_percentage: float

    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, config: PricingConfig) -> "PricingConfigResponse":
        """Create response from PricingConfig model."""
        return cls(
            id=config.id,
            tier_id=config.tier_id,
            tier_name=config.tier_name,
            description=config.description,
            base_llm_cost_per_minute=float(config.base_llm_cost_per_minute),
            base_stt_cost_per_minute=float(config.base_stt_cost_per_minute),
            base_tts_cost_per_minute=float(config.base_tts_cost_per_minute),
            base_telephony_cost_per_minute=float(config.base_telephony_cost_per_minute),
            total_base_cost_per_minute=float(config.total_base_cost_per_minute),
            ai_markup_percentage=float(config.ai_markup_percentage),
            telephony_markup_percentage=float(config.telephony_markup_percentage),
            final_ai_price_per_minute=float(config.final_ai_price_per_minute),
            final_telephony_price_per_minute=float(config.final_telephony_price_per_minute),
            final_total_price_per_minute=float(config.final_total_price_per_minute),
            profit_per_minute=float(config.profit_per_minute),
            profit_margin_percentage=float(config.profit_margin_percentage),
            updated_at=config.updated_at.isoformat() if config.updated_at else "",
        )


class PricingConfigCreate(BaseModel):
    """Request to create a pricing configuration."""

    tier_id: str = Field(..., min_length=1, max_length=50)
    tier_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

    base_llm_cost_per_minute: float = Field(..., ge=0)
    base_stt_cost_per_minute: float = Field(..., ge=0)
    base_tts_cost_per_minute: float = Field(..., ge=0)
    base_telephony_cost_per_minute: float = Field(..., ge=0)

    ai_markup_percentage: float = Field(default=30.0, ge=0, le=500)
    telephony_markup_percentage: float = Field(default=20.0, ge=0, le=500)


class PricingConfigUpdate(BaseModel):
    """Request to update pricing configuration (mainly markups)."""

    tier_name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None

    base_llm_cost_per_minute: float | None = Field(None, ge=0)
    base_stt_cost_per_minute: float | None = Field(None, ge=0)
    base_tts_cost_per_minute: float | None = Field(None, ge=0)
    base_telephony_cost_per_minute: float | None = Field(None, ge=0)

    ai_markup_percentage: float | None = Field(None, ge=0, le=500)
    telephony_markup_percentage: float | None = Field(None, ge=0, le=500)


# =============================================================================
# Pricing Admin Endpoints
# =============================================================================


@router.get("/pricing", response_model=list[PricingConfigResponse])
async def list_pricing_configs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[PricingConfigResponse]:
    """List all pricing configurations."""
    require_admin(current_user)

    result = await db.execute(select(PricingConfig).order_by(PricingConfig.tier_id))
    configs = result.scalars().all()

    return [PricingConfigResponse.from_model(config) for config in configs]


@router.post("/pricing", response_model=PricingConfigResponse)
async def create_pricing_config(
    body: PricingConfigCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PricingConfigResponse:
    """Create a new pricing configuration."""
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id, tier_id=body.tier_id)
    log.info("creating_pricing_config")

    # Check if tier_id already exists
    result = await db.execute(select(PricingConfig).where(PricingConfig.tier_id == body.tier_id))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pricing config for tier '{body.tier_id}' already exists",
        )

    # Create the config
    config = PricingConfig(
        tier_id=body.tier_id,
        tier_name=body.tier_name,
        description=body.description,
        base_llm_cost_per_minute=Decimal(str(body.base_llm_cost_per_minute)),
        base_stt_cost_per_minute=Decimal(str(body.base_stt_cost_per_minute)),
        base_tts_cost_per_minute=Decimal(str(body.base_tts_cost_per_minute)),
        base_telephony_cost_per_minute=Decimal(str(body.base_telephony_cost_per_minute)),
        ai_markup_percentage=Decimal(str(body.ai_markup_percentage)),
        telephony_markup_percentage=Decimal(str(body.telephony_markup_percentage)),
        # These will be recalculated
        final_ai_price_per_minute=Decimal("0"),
        final_telephony_price_per_minute=Decimal("0"),
        final_total_price_per_minute=Decimal("0"),
    )
    config.recalculate_prices()

    db.add(config)
    await db.commit()
    await db.refresh(config)

    log.info("pricing_config_created", config_id=config.id)
    return PricingConfigResponse.from_model(config)


@router.get("/pricing/{tier_id}", response_model=PricingConfigResponse)
async def get_pricing_config(
    tier_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PricingConfigResponse:
    """Get a specific pricing configuration by tier ID."""
    require_admin(current_user)

    result = await db.execute(select(PricingConfig).where(PricingConfig.tier_id == tier_id))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config for tier '{tier_id}' not found",
        )

    return PricingConfigResponse.from_model(config)


@router.put("/pricing/{tier_id}", response_model=PricingConfigResponse)
async def update_pricing_config(
    tier_id: str,
    body: PricingConfigUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PricingConfigResponse:
    """Update a pricing configuration (base costs and/or markups)."""
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id, tier_id=tier_id)
    log.info("updating_pricing_config")

    result = await db.execute(select(PricingConfig).where(PricingConfig.tier_id == tier_id))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config for tier '{tier_id}' not found",
        )

    # Update fields if provided
    if body.tier_name is not None:
        config.tier_name = body.tier_name
    if body.description is not None:
        config.description = body.description
    if body.base_llm_cost_per_minute is not None:
        config.base_llm_cost_per_minute = Decimal(str(body.base_llm_cost_per_minute))
    if body.base_stt_cost_per_minute is not None:
        config.base_stt_cost_per_minute = Decimal(str(body.base_stt_cost_per_minute))
    if body.base_tts_cost_per_minute is not None:
        config.base_tts_cost_per_minute = Decimal(str(body.base_tts_cost_per_minute))
    if body.base_telephony_cost_per_minute is not None:
        config.base_telephony_cost_per_minute = Decimal(str(body.base_telephony_cost_per_minute))
    if body.ai_markup_percentage is not None:
        config.ai_markup_percentage = Decimal(str(body.ai_markup_percentage))
    if body.telephony_markup_percentage is not None:
        config.telephony_markup_percentage = Decimal(str(body.telephony_markup_percentage))

    # Recalculate final prices
    config.recalculate_prices()

    await db.commit()
    await db.refresh(config)

    log.info("pricing_config_updated", config_id=config.id)
    return PricingConfigResponse.from_model(config)


@router.delete("/pricing/{tier_id}")
async def delete_pricing_config(
    tier_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a pricing configuration."""
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id, tier_id=tier_id)

    result = await db.execute(select(PricingConfig).where(PricingConfig.tier_id == tier_id))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing config for tier '{tier_id}' not found",
        )

    await db.delete(config)
    await db.commit()

    log.info("pricing_config_deleted")
    return {"message": f"Pricing config for tier '{tier_id}' deleted successfully"}


@router.post("/pricing/seed-defaults")
async def seed_default_pricing_configs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Seed default pricing configurations for all tiers.

    This creates pricing configs with estimated base costs and default markups.
    Costs are approximate based on provider pricing as of 2025.
    """
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id)
    log.info("seeding_default_pricing_configs")

    # Default tier configurations - base costs + markups to achieve target prices
    # Target prices: Premium=$0.10, Premium Mini=$0.07, Balanced=$0.07, Budget=$0.05
    default_configs = [
        {
            "tier_id": "premium",
            "tier_name": "Premium",
            "description": "Best quality with OpenAI's latest gpt-realtime model",
            # Base costs (what we pay providers)
            "base_llm_cost_per_minute": Decimal("0.024"),  # OpenAI Realtime
            "base_stt_cost_per_minute": Decimal("0.003"),  # Built into realtime
            "base_tts_cost_per_minute": Decimal("0.003"),  # Built into realtime
            "base_telephony_cost_per_minute": Decimal("0.008"),  # Telnyx
            # Markups: 200% AI = 3x, 25% telephony = 1.25x → Final: $0.10/min
            "ai_markup_percentage": Decimal("200.00"),
            "telephony_markup_percentage": Decimal("25.00"),
        },
        {
            "tier_id": "premium-mini",
            "tier_name": "Premium Mini",
            "description": "OpenAI Realtime at a fraction of the cost",
            "base_llm_cost_per_minute": Decimal("0.011"),  # GPT-4o-mini realtime
            "base_stt_cost_per_minute": Decimal("0.002"),
            "base_tts_cost_per_minute": Decimal("0.002"),
            "base_telephony_cost_per_minute": Decimal("0.008"),
            # Markups: 300% AI = 4x → Final: $0.07/min
            "ai_markup_percentage": Decimal("300.00"),
            "telephony_markup_percentage": Decimal("25.00"),
        },
        {
            "tier_id": "balanced",
            "tier_name": "Balanced",
            "description": "Best performance-to-cost ratio with multimodal capabilities",
            "base_llm_cost_per_minute": Decimal("0.014"),  # Gemini
            "base_stt_cost_per_minute": Decimal("0.003"),
            "base_tts_cost_per_minute": Decimal("0.003"),
            "base_telephony_cost_per_minute": Decimal("0.008"),
            # Markups: 200% AI = 3x → Final: $0.07/min
            "ai_markup_percentage": Decimal("200.00"),
            "telephony_markup_percentage": Decimal("25.00"),
        },
        {
            "tier_id": "budget",
            "tier_name": "Budget",
            "description": "Maximum cost savings - perfect for high-volume operations",
            "base_llm_cost_per_minute": Decimal("0.007"),  # Cerebras/Llama
            "base_stt_cost_per_minute": Decimal("0.003"),  # Deepgram
            "base_tts_cost_per_minute": Decimal("0.003"),  # ElevenLabs
            "base_telephony_cost_per_minute": Decimal("0.008"),
            # Markups: 200% AI = 3x → Final: $0.05/min
            "ai_markup_percentage": Decimal("200.00"),
            "telephony_markup_percentage": Decimal("25.00"),
        },
    ]

    created_count = 0
    skipped_count = 0

    for config_data in default_configs:
        # Check if already exists
        result = await db.execute(
            select(PricingConfig).where(PricingConfig.tier_id == config_data["tier_id"])
        )
        if result.scalar_one_or_none():
            skipped_count += 1
            continue

        config = PricingConfig(
            tier_id=config_data["tier_id"],
            tier_name=config_data["tier_name"],
            description=config_data["description"],
            base_llm_cost_per_minute=config_data["base_llm_cost_per_minute"],
            base_stt_cost_per_minute=config_data["base_stt_cost_per_minute"],
            base_tts_cost_per_minute=config_data["base_tts_cost_per_minute"],
            base_telephony_cost_per_minute=config_data["base_telephony_cost_per_minute"],
            ai_markup_percentage=config_data["ai_markup_percentage"],
            telephony_markup_percentage=config_data["telephony_markup_percentage"],
            final_ai_price_per_minute=Decimal("0"),
            final_telephony_price_per_minute=Decimal("0"),
            final_total_price_per_minute=Decimal("0"),
        )
        config.recalculate_prices()
        db.add(config)
        created_count += 1

    await db.commit()

    log.info("pricing_configs_seeded", created=created_count, skipped=skipped_count)
    return {"message": f"Seeded {created_count} pricing configs, skipped {skipped_count} existing"}


# =============================================================================
# Access Token Pydantic Models
# =============================================================================


def generate_access_token() -> str:
    """Generate a secure access token with sv_at_ prefix."""
    random_part = secrets.token_urlsafe(32)
    return f"sv_at_{random_part}"


class CreateAccessTokenRequest(BaseModel):
    """Request to create a one-time access token."""

    label: str | None = Field(None, max_length=255)
    expires_in_hours: int = Field(default=24, ge=1, le=72)
    is_read_only: bool = True
    notes: str | None = None


class AccessTokenResponse(BaseModel):
    """Response for a created access token."""

    id: int
    token: str
    url: str
    label: str | None
    expires_at: str
    is_read_only: bool
    status: str
    created_at: str
    used_at: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, token: AccessToken, include_token: bool = True) -> "AccessTokenResponse":
        """Create response from AccessToken model."""
        # Build the access URL
        frontend_url = getattr(settings, "FRONTEND_URL", "https://dashboard.spacevoice.ai")
        url = f"{frontend_url}/access/{token.token}" if include_token else ""

        return cls(
            id=token.id,
            token=token.token if include_token else "***",
            url=url,
            label=token.label,
            expires_at=token.expires_at.isoformat() if token.expires_at else "",
            is_read_only=token.is_read_only,
            status=token.status,
            created_at=token.created_at.isoformat() if token.created_at else "",
            used_at=token.used_at.isoformat() if token.used_at else None,
        )


class AccessTokenListResponse(BaseModel):
    """Response for listing access tokens (without full token)."""

    id: int
    token_preview: str  # Shows only first/last few chars
    label: str | None
    expires_at: str
    is_read_only: bool
    status: str
    created_at: str
    used_at: str | None = None
    used_by_ip: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, token: AccessToken) -> "AccessTokenListResponse":
        """Create response from AccessToken model."""
        # Show only preview: sv_at_abc...xyz
        preview = (
            f"{token.token[:10]}...{token.token[-4:]}" if len(token.token) > 14 else token.token
        )

        return cls(
            id=token.id,
            token_preview=preview,
            label=token.label,
            expires_at=token.expires_at.isoformat() if token.expires_at else "",
            is_read_only=token.is_read_only,
            status=token.status,
            created_at=token.created_at.isoformat() if token.created_at else "",
            used_at=token.used_at.isoformat() if token.used_at else None,
            used_by_ip=token.used_by_ip,
        )


# =============================================================================
# Access Token Admin Endpoints
# =============================================================================


@router.post("/access-tokens", response_model=AccessTokenResponse)
async def create_access_token(
    body: CreateAccessTokenRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """Generate a new one-time access token for dashboard access.

    This creates a secure, single-use URL that grants temporary access
    to the dashboard for superior review.
    """
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id, label=body.label)
    log.info("creating_access_token")

    # Generate unique token
    token_value = generate_access_token()
    while True:
        result = await db.execute(select(AccessToken).where(AccessToken.token == token_value))
        if not result.scalar_one_or_none():
            break
        token_value = generate_access_token()

    # Calculate expiration
    expires_at = datetime.now(UTC) + timedelta(hours=body.expires_in_hours)

    # Create token
    access_token = AccessToken(
        token=token_value,
        created_by_id=current_user.id,
        expires_at=expires_at,
        label=body.label,
        is_read_only=body.is_read_only,
        notes=body.notes,
    )
    db.add(access_token)
    await db.commit()
    await db.refresh(access_token)

    log.info("access_token_created", token_id=access_token.id, expires_at=expires_at.isoformat())
    return AccessTokenResponse.from_model(access_token, include_token=True)


@router.get("/access-tokens", response_model=list[AccessTokenListResponse])
async def list_access_tokens(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[AccessTokenListResponse]:
    """List all access tokens created by the current admin."""
    require_admin(current_user)

    result = await db.execute(
        select(AccessToken)
        .where(AccessToken.created_by_id == current_user.id)
        .order_by(AccessToken.created_at.desc())
    )
    tokens = result.scalars().all()

    return [AccessTokenListResponse.from_model(token) for token in tokens]


@router.delete("/access-tokens/{token_id}")
async def revoke_access_token(
    token_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke an access token."""
    require_admin_write(current_user)

    log = logger.bind(admin_id=current_user.id, token_id=token_id)

    result = await db.execute(
        select(AccessToken).where(
            AccessToken.id == token_id,
            AccessToken.created_by_id == current_user.id,
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access token not found",
        )

    if token.revoked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token already revoked",
        )

    token.revoked_at = datetime.now(UTC)
    await db.commit()

    log.info("access_token_revoked")
    return {"message": "Access token revoked successfully"}
