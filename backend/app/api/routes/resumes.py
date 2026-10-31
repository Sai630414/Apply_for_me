import os
import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.schemas.resume import ResumeResponse, ResumeCreate

router = APIRouter(prefix="/resumes", tags=["Resumes"])

UPLOAD_DIR = Path("uploads/resumes")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal or unsafe characters."""
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
    return clean or "resume.pdf"


@router.get("", response_model=List[ResumeResponse])
async def list_resumes(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """List all resumes uploaded by the authenticated user."""
    user_id = str(current_user["_id"])
    if db is None:
        return []

    cursor = db.resumes.find({"userId": user_id}).sort("uploadedAt", -1)
    resumes = []
    async for r in cursor:
        r["_id"] = str(r["_id"])
        resumes.append(r)
    return resumes


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    title: Optional[str] = Form("My Resume"),
    category: Optional[str] = Form("General"),
    isDefault: Optional[bool] = Form(False),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Upload a PDF resume file for the authenticated user.
    Enforces PDF format and 5MB size limit.
    """
    user_id = str(current_user["_id"])

    # 1. Validate file extension and MIME type
    original_filename = file.filename or "resume.pdf"
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    # 2. Read contents and check size limit (5MB)
    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the 5MB limit ({file_size / (1024 * 1024):.2f}MB)."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 3. Store on disk using local storage adapter
    user_upload_dir = UPLOAD_DIR / user_id
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(original_filename)
    unique_prefix = uuid.uuid4().hex[:8]
    stored_name = f"{unique_prefix}_{safe_name}"
    file_path = user_upload_dir / stored_name

    with open(file_path, "wb") as f:
        f.write(contents)

    # 4. Check if default
    count = 0
    if db is not None:
        count = await db.resumes.count_documents({"userId": user_id})

    # If first resume or explicitly set as default, mark as default
    should_be_default = isDefault or count == 0

    if should_be_default and db is not None:
        await db.resumes.update_many(
            {"userId": user_id},
            {"$set": {"isDefault": False}}
        )

    now = datetime.now(timezone.utc)
    doc_id = str(ObjectId())

    doc = {
        "_id": doc_id,
        "userId": user_id,
        "title": title or "My Resume",
        "fileName": safe_name,
        "storedFileName": stored_name,
        "fileUrl": f"/api/resumes/{doc_id}/file",
        "contentType": "application/pdf",
        "category": category or "General",
        "fileSize": file_size,
        "isDefault": should_be_default,
        "uploadedAt": now
    }

    if db is not None:
        # Use ObjectId in Mongo
        mongo_doc = dict(doc)
        mongo_doc["_id"] = ObjectId(doc_id)
        await db.resumes.insert_one(mongo_doc)

    return doc


@router.get("/{resume_id}/file")
async def get_resume_file(
    resume_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Stream / download the PDF resume file for the authenticated user."""
    user_id = str(current_user["_id"])
    resume = None
    if db is not None:
        try:
            resume = await db.resumes.find_one({"_id": ObjectId(resume_id), "userId": user_id})
        except Exception:
            resume = await db.resumes.find_one({"_id": resume_id, "userId": user_id})

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    stored_name = resume.get("storedFileName")
    if not stored_name:
        raise HTTPException(status_code=404, detail="Resume file missing")

    file_path = UPLOAD_DIR / user_id / stored_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=resume.get("fileName", "resume.pdf")
    )


@router.patch("/{resume_id}/default", response_model=ResumeResponse)
async def set_default_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Set a specific resume as the default."""
    user_id = str(current_user["_id"])
    if db is not None:
        # Clear default flag on all resumes
        await db.resumes.update_many(
            {"userId": user_id},
            {"$set": {"isDefault": False}}
        )
        try:
            oid = ObjectId(resume_id)
            res = await db.resumes.find_one_and_update(
                {"_id": oid, "userId": user_id},
                {"$set": {"isDefault": True}},
                return_document=True
            )
        except Exception:
            res = await db.resumes.find_one_and_update(
                {"_id": resume_id, "userId": user_id},
                {"$set": {"isDefault": True}},
                return_document=True
            )

        if not res:
            raise HTTPException(status_code=404, detail="Resume not found")

        res["_id"] = str(res["_id"])
        return res

    return {
        "_id": resume_id,
        "userId": user_id,
        "title": "Default Resume",
        "fileName": "resume.pdf",
        "fileUrl": f"/api/resumes/{resume_id}/file",
        "contentType": "application/pdf",
        "category": "General",
        "fileSize": 1024,
        "isDefault": True,
        "uploadedAt": datetime.now(timezone.utc)
    }


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Delete a resume by ID."""
    user_id = str(current_user["_id"])
    if db is not None:
        resume = None
        try:
            oid = ObjectId(resume_id)
            resume = await db.resumes.find_one({"_id": oid, "userId": user_id})
            if resume:
                await db.resumes.delete_one({"_id": oid, "userId": user_id})
        except Exception:
            resume = await db.resumes.find_one({"_id": resume_id, "userId": user_id})
            if resume:
                await db.resumes.delete_one({"_id": resume_id, "userId": user_id})

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Clean up disk file
        stored_name = resume.get("storedFileName")
        if stored_name:
            file_path = UPLOAD_DIR / user_id / stored_name
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

        # If deleted resume was default, set the newest remaining resume as default
        if resume.get("isDefault"):
            newest = await db.resumes.find_one({"userId": user_id}, sort=[("uploadedAt", -1)])
            if newest:
                await db.resumes.update_one({"_id": newest["_id"]}, {"$set": {"isDefault": True}})

    return {"status": "success", "message": "Resume deleted successfully"}
