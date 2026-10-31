from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationStatus
)

router = APIRouter(prefix="/applications", tags=["Job Applications Tracker"])


@router.get("", response_model=List[ApplicationResponse])
async def list_applications(
    status_filter: Optional[ApplicationStatus] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieve user's job application history."""
    user_id = str(current_user["_id"])
    if db is None:
        return []

    query = {"userId": user_id}
    if status_filter:
        query["status"] = status_filter.value

    cursor = db.applications.find(query).sort("appliedAt", -1)
    apps = []
    async for a in cursor:
        a["_id"] = str(a["_id"])
        apps.append(a)
    return apps


@router.post("", response_model=ApplicationResponse)
async def create_application(
    payload: ApplicationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Log a new job application."""
    user_id = str(current_user["_id"])
    doc = {
        "userId": user_id,
        "companyName": payload.companyName,
        "jobTitle": payload.jobTitle,
        "jobUrl": payload.jobUrl,
        "resumeId": payload.resumeId,
        "status": payload.status.value,
        "notes": payload.notes,
        "appliedAt": datetime.now(timezone.utc)
    }

    if db is not None:
        res = await db.applications.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
    else:
        doc["_id"] = "dev_app_123"

    return doc


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update job application status or details."""
    user_id = str(current_user["_id"])
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "status" in update_data and isinstance(update_data["status"], ApplicationStatus):
        update_data["status"] = update_data["status"].value

    if db is not None:
        try:
            oid = ObjectId(application_id)
            filter_q = {"_id": oid, "userId": user_id}
        except Exception:
            filter_q = {"_id": application_id, "userId": user_id}

        result = await db.applications.update_one(filter_q, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Application record not found")

        updated = await db.applications.find_one(filter_q)
        updated["_id"] = str(updated["_id"])
        return updated

    update_data["_id"] = application_id
    update_data["userId"] = user_id
    update_data["appliedAt"] = datetime.now(timezone.utc)
    return update_data

