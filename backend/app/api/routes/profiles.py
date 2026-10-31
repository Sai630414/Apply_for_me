from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdate,
    ProfileCreate,
    ProfilePatch,
    ProfileCompletionResponse
)
from app.services.profile_service import ProfileService

router = APIRouter(tags=["Profiles"])


@router.get("/me", response_model=ProfileResponse)
@router.get("", response_model=ProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get the applicant profile for the authenticated user.
    Calculates and returns live completion percentage.
    """
    user_id = str(current_user["_id"])
    return await ProfileService.get_user_profile(user_id, db)


@router.get("/me/completion", response_model=ProfileCompletionResponse)
@router.get("/completion", response_model=ProfileCompletionResponse)
async def get_profile_completion(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get completion percentage, missing required fields, and actionable suggestions.
    """
    user_id = str(current_user["_id"])
    return await ProfileService.get_completion_details(user_id, db)


@router.post("", response_model=ProfileResponse)
async def create_profile(
    profile_in: ProfileCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Create a new applicant profile for the authenticated user.
    If a profile already exists, performs an upsert/update.
    """
    user_id = str(current_user["_id"])
    return await ProfileService.create_user_profile(user_id, profile_in.model_dump(), db)


@router.put("/me", response_model=ProfileResponse)
@router.put("", response_model=ProfileResponse)
async def update_profile(
    profile_in: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Full profile update for the authenticated user.
    """
    user_id = str(current_user["_id"])
    return await ProfileService.update_user_profile(user_id, profile_in.model_dump(), db)


@router.patch("/me", response_model=ProfileResponse)
@router.patch("", response_model=ProfileResponse)
async def patch_profile(
    patch_in: ProfilePatch,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Partial update for specific profile sections (e.g. personal info, skills, education).
    """
    user_id = str(current_user["_id"])
    # Exclude unset fields so only provided sections get modified
    patch_dict = patch_in.model_dump(exclude_unset=True)
    return await ProfileService.patch_user_profile(user_id, patch_dict, db)
