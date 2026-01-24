"""Authentication API routes."""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.access_token import AccessToken
from app.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Pydantic Models
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str  # Will be used as full_name
    password: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response."""

    id: int
    email: str
    username: str | None = None  # Maps to full_name
    onboarding_completed: bool = False
    onboarding_step: int = 1
    is_superuser: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: "User") -> "UserResponse":
        """Create response from User model."""
        return cls(
            id=user.id,
            email=user.email,
            username=user.full_name,
            onboarding_completed=user.onboarding_completed,
            onboarding_step=user.onboarding_step,
            is_superuser=user.is_superuser,
        )


# =============================================================================
# Helper Functions
# =============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject of the token (user ID or email)
        expires_delta: Optional custom expiration time. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# =============================================================================
# Auth Endpoints
# =============================================================================


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")  # Strict rate limit to prevent account spam
async def register(
    body: RegisterRequest,
    request: Request,  # Required for rate limiter
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user.

    Args:
        body: Registration request with email, username, password
        db: Database session

    Returns:
        Created user
    """
    log = logger.bind(email=body.email, username=body.username)
    log.info("registering_user")

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user (username is stored as full_name)
    user = User(
        email=body.email,
        full_name=body.username,
        hashed_password=get_password_hash(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    log.info("user_registered", user_id=user.id)
    return UserResponse.from_user(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # Strict rate limit to prevent brute force attacks
async def login(
    request: Request,  # Required for rate limiter
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login and get an access token.

    Supports login with:
    - Email (for admins)
    - Client ID (for clients)

    Args:
        form_data: OAuth2 form with username (email or client_id) and password
        db: Database session

    Returns:
        Access token
    """
    log = logger.bind(username=form_data.username)
    log.info("login_attempt")

    # Try to find user by email first (for admins), then by client_id (for clients)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user:
        # Try client_id lookup
        result = await db.execute(select(User).where(User.client_id == form_data.username))
        user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        log.warning("login_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    log.info("login_success", user_id=user.id)

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information.

    Args:
        current_user: Authenticated user

    Returns:
        User information
    """
    return UserResponse.from_user(current_user)


# =============================================================================
# Access Token Endpoints
# =============================================================================


class AccessTokenLoginResponse(BaseModel):
    """Response for access token login."""

    access_token: str
    token_type: str = "bearer"
    is_read_only: bool
    user: UserResponse


@router.get("/access/{token}", response_model=AccessTokenLoginResponse)
async def consume_access_token(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AccessTokenLoginResponse:
    """Consume a one-time access token and receive a JWT.

    This endpoint validates the token, marks it as used, and returns
    a JWT that grants access to the dashboard.

    Args:
        token: The one-time access token (sv_at_xxx format)
        request: Request object (for IP logging)
        db: Database session

    Returns:
        JWT access token and user info
    """
    log = logger.bind(token_prefix=token[:14] if len(token) > 14 else token)
    log.info("access_token_consumption_attempt")

    # Find the token
    result = await db.execute(select(AccessToken).where(AccessToken.token == token))
    access_token = result.scalar_one_or_none()

    if not access_token:
        log.warning("access_token_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired access link",
        )

    # Check if already used
    if access_token.used_at:
        log.warning("access_token_already_used")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This access link has already been used",
        )

    # Check if revoked
    if access_token.revoked_at:
        log.warning("access_token_revoked")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This access link has been revoked",
        )

    # Check if expired
    now = datetime.now(UTC)
    if access_token.expires_at <= now:
        log.warning("access_token_expired")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This access link has expired",
        )

    # Get the admin user who created the token
    user_result = await db.execute(select(User).where(User.id == access_token.created_by_id))
    token_user: User | None = user_result.scalar_one_or_none()

    if not token_user:
        log.error("access_token_user_not_found")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated user not found",
        )

    # Mark token as used
    client_ip = request.client.host if request.client else "unknown"
    access_token.used_at = now
    access_token.used_by_ip = client_ip
    await db.commit()

    # Create JWT with read_only claim if applicable
    jwt_payload = {"sub": str(token_user.id), "exp": now + timedelta(hours=24)}
    if access_token.is_read_only:
        jwt_payload["read_only"] = True

    jwt_token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    log.info(
        "access_token_consumed",
        token_id=access_token.id,
        user_id=token_user.id,
        is_read_only=access_token.is_read_only,
        client_ip=client_ip,
    )

    return AccessTokenLoginResponse(
        access_token=jwt_token,
        is_read_only=access_token.is_read_only,
        user=UserResponse.from_user(token_user),
    )
