"""Authentication and user management API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth.dependencies import (
    get_auth_provider,
    get_current_user,
    get_jwt_handler,
    require_admin_role,
)
from ..auth.jwt_handler import JWTHandler
from ..auth.models import (
    APIKey,
    APIKeyCreate,
    APIKeyResponse,
    TokenResponse,
    User,
    UserCreate,
    UserLogin,
)
from ..auth.providers import AuthProvider

logger = logging.getLogger(__name__)


def create_auth_router() -> APIRouter:
    """Create authentication router with all auth endpoints."""
    router = APIRouter(prefix="/auth", tags=["Authentication"])

    @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    async def register_user(
        user_data: UserCreate,
        auth_provider: AuthProvider = Depends(get_auth_provider),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
    ) -> TokenResponse:
        """Register a new user account."""
        try:
            # Create the user
            user = await auth_provider.create_user(user_data)

            # Generate access token
            access_token = jwt_handler.create_access_token(user)

            # Update last login
            await auth_provider.update_last_login(user.id)

            logger.info(f"User registered successfully: {user.username}")

            return TokenResponse(
                access_token=access_token,
                expires_in=jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )

    @router.post("/login", response_model=TokenResponse)
    async def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        auth_provider: AuthProvider = Depends(get_auth_provider),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
    ) -> TokenResponse:
        """Authenticate user and return access token."""
        user = await auth_provider.authenticate_user(
            form_data.username,
            form_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate access token
        access_token = jwt_handler.create_access_token(user)

        # Update last login
        await auth_provider.update_last_login(user.id)

        logger.info(f"User logged in: {user.username}")

        return TokenResponse(
            access_token=access_token,
            expires_in=jwt_handler.settings.access_token_expire_minutes * 60,
            user=user
        )

    @router.post("/login/json", response_model=TokenResponse)
    async def login_user_json(
        login_data: UserLogin,
        auth_provider: AuthProvider = Depends(get_auth_provider),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
    ) -> TokenResponse:
        """Authenticate user with JSON payload and return access token."""
        user = await auth_provider.authenticate_user(
            login_data.username,
            login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate access token
        access_token = jwt_handler.create_access_token(user)

        # Update last login
        await auth_provider.update_last_login(user.id)

        logger.info(f"User logged in via JSON: {user.username}")

        return TokenResponse(
            access_token=access_token,
            expires_in=jwt_handler.settings.access_token_expire_minutes * 60,
            user=user
        )

    @router.get("/me", response_model=User)
    async def get_current_user_info(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Get current user information."""
        return current_user

    @router.post("/api-keys", response_model=APIKeyResponse)
    async def create_api_key(
        key_data: APIKeyCreate,
        current_user: User = Depends(get_current_user),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> APIKeyResponse:
        """Create a new API key for the current user."""
        try:
            api_key_model, actual_key = await auth_provider.create_api_key(
                current_user.id,
                key_data
            )

            logger.info(f"API key created: {key_data.name} for user {current_user.username}")

            return APIKeyResponse(
                id=api_key_model.id,
                name=api_key_model.name,
                description=api_key_model.description,
                api_key=actual_key,  # Only shown here, never again
                expires_at=api_key_model.expires_at
            )

        except Exception as e:
            logger.error(f"API key creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )

    @router.get("/api-keys", response_model=list[APIKey])
    async def list_api_keys(
        current_user: User = Depends(get_current_user),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> list[APIKey]:
        """List all API keys for the current user."""
        if hasattr(auth_provider, 'list_user_api_keys'):
            return await auth_provider.list_user_api_keys(current_user.id)
        else:
            # Fallback for providers that don't implement this method
            return []

    @router.delete("/api-keys/{key_id}")
    async def revoke_api_key(
        key_id: UUID,
        current_user: User = Depends(get_current_user),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> dict:
        """Revoke an API key."""
        success = await auth_provider.revoke_api_key(current_user.id, key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        logger.info(f"API key {key_id} revoked by user {current_user.username}")
        return {"message": "API key revoked successfully"}

    # Admin-only endpoints
    @router.post("/admin/users", response_model=User)
    async def create_user_admin(
        user_data: UserCreate,
        _admin: User = Depends(require_admin_role),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> User:
        """Admin endpoint to create users."""
        try:
            user = await auth_provider.create_user(user_data)
            logger.info(f"Admin created user: {user.username}")
            return user
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    @router.get("/admin/users/{user_id}", response_model=User)
    async def get_user_admin(
        user_id: UUID,
        _admin: User = Depends(require_admin_role),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> User:
        """Admin endpoint to get user by ID."""
        user = await auth_provider.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    return router
