from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    title: str = "My Resume"
    fileName: str
    fileUrl: str
    contentType: str = "application/pdf"
    category: Optional[str] = "General"
    fileSize: Optional[int] = None
    isDefault: bool = False


class ResumeCreate(ResumeBase):
    pass


class ResumeResponse(ResumeBase):
    id: str = Field(alias="_id")
    userId: str
    uploadedAt: datetime

    class Config:
        populate_by_name = True
