from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_user(current_user: dict = Depends(get_current_user)):
    return current_user


@router.delete("/me")
async def delete_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Permanently delete user account and all associated profile, resumes,
    applications, and AI records (GDPR/Privacy compliance).
    """
    user_id = str(current_user["_id"])
    if db is not None:
        try:
            obj_id = ObjectId(user_id)
            await db.users.delete_one({"_id": obj_id})
        except Exception:
            await db.users.delete_one({"_id": user_id})

        await db.profiles.delete_many({"userId": user_id})
        await db.resumes.delete_many({"userId": user_id})
        await db.applications.delete_many({"userId": user_id})
        await db.generated_answers.delete_many({"userId": user_id})
        await db.preferences.delete_many({"userId": user_id})

    return {"status": "success", "message": "User account and all associated data deleted successfully."}

