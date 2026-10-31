from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.schemas.auth import GoogleAuthRequest, DevLoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.seeder_service import seed_sample_development_account

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/google", response_model=TokenResponse)
async def authenticate_google(
    payload: GoogleAuthRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Authenticate using Google OAuth 2.0 ID Token.
    Returns access token and user information.
    """
    auth_data = await AuthService.authenticate_google_user(payload.id_token, db)
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google OAuth token or verification failed"
        )
    return auth_data


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(
    payload: DevLoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Development login endpoint for testing without live Google Client ID.
    Enables rapid local developer onboarding and extension testing.
    Only available in development / test environments.
    """
    # 1. Reject in production
    if settings.APP_ENV == "production" and not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development login is disabled in production environments."
        )

    # 2. Reject arbitrary emails outside test suite
    email_clean = payload.email.lower().strip()
    allowed_emails = {"saikondareddypala@gmail.com"}
    
    if settings.APP_ENV not in ("test",) and email_clean not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dev login is restricted to the development account: saikondareddypala@gmail.com"
        )

    # 3. Ensure profile is seeded for the sample dev account
    if email_clean == "saikondareddypala@gmail.com":
        await seed_sample_development_account(db)

    return await AuthService.dev_login(payload.email, payload.name, db)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Log out user and acknowledge session termination.
    """
    return {"message": "Logged out successfully", "user_id": str(current_user.get("_id"))}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve currently authenticated user's information.
    """
    return current_user

