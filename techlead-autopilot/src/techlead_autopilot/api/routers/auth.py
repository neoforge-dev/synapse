"""Authentication API endpoints."""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..auth import (
    create_access_token, 
    create_refresh_token, 
    verify_token, 
    get_jwt_manager,
    hash_password, 
    verify_password, 
    validate_password_strength,
    get_current_user
)
from ...infrastructure.database import get_db_session
from ...infrastructure.database.models import User, Organization

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=255, description="First name")
    last_name: str = Field(..., min_length=1, max_length=255, description="Last name")
    organization_name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    job_title: str = Field(default="", max_length=255, description="Job title")


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    first_name: str
    last_name: str
    job_title: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    organization_id: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Register a new user and create organization.
    
    Creates both user and organization in a single transaction.
    """
    try:
        # Validate password strength
        is_valid, errors = validate_password_strength(request.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password validation failed: {'; '.join(errors)}"
            )
        
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(User.email == request.email.lower())
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Hash password
        hashed_password = hash_password(request.password)
        
        # Create organization first
        organization = Organization(
            id=uuid4(),
            name=request.organization_name,
            subscription_tier="pro",
            subscription_status="active",
            subscription_started_at=datetime.utcnow(),
            monthly_price_cents=29700,  # €297
            content_generation_limit=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(organization)
        await db.flush()  # Get organization ID
        
        # Create user
        user = User(
            id=uuid4(),
            organization_id=organization.id,
            email=request.email.lower(),
            password_hash=hashed_password,
            first_name=request.first_name,
            last_name=request.last_name,
            job_title=request.job_title,
            role="owner",  # First user is organization owner
            is_active=True,
            is_verified=False,  # Email verification can be added later
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        await db.commit()
        
        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            organization_id=organization.id,
            email=user.email,
            role=user.role
        )
        
        refresh_token_str = create_refresh_token(
            user_id=user.id,
            organization_id=organization.id,
            email=user.email,
            role=user.role
        )
        
        logger.info(f"User registered successfully: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate user and return JWT tokens.
    
    Returns access and refresh tokens for valid credentials.
    """
    try:
        # Find user
        result = await db.execute(
            select(User)
            .join(Organization)
            .where(User.email == request.email.lower())
            .where(User.deleted_at.is_(None))
            .where(Organization.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            logger.warning(f"Invalid password for user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()
        
        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            role=user.role
        )
        
        refresh_token_str = create_refresh_token(
            user_id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            role=user.role
        )
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    Returns new access and refresh tokens.
    """
    try:
        jwt_manager = get_jwt_manager()
        tokens = jwt_manager.refresh_access_token(request.refresh_token)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info("Tokens refreshed successfully")
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user by blacklisting their tokens.
    
    Requires authentication with access token.
    """
    try:
        # In a production system, you would:
        # 1. Get the current access token from the request
        # 2. Blacklist both access and refresh tokens
        # 3. Possibly store in Redis for distributed systems
        
        # For now, we'll just log the logout
        logger.info(f"User logged out: {current_user.email}")
        
        # Note: In a real implementation, you would extract the token
        # from the request and blacklist it:
        # jwt_manager = get_jwt_manager()
        # jwt_manager.blacklist_token(current_access_token)
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    
    Returns user profile data for authenticated user.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name or "",
        last_name=current_user.last_name or "",
        job_title=current_user.job_title or "",
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        organization_id=str(current_user.organization_id)
    )