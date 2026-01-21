"""Admin API routes for managing clients."""

import secrets
import string

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_password_hash
from app.core.auth import CurrentUser
from app.db.session import get_db
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
    """Require the current user to be an admin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
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
    require_admin(current_user)

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
    require_admin(current_user)

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
