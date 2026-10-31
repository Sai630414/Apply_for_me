from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    DRAFT = "Draft"
    APPLIED = "Applied"
    INTERVIEW = "Interview"
    REJECTED = "Rejected"
    SELECTED = "Selected"


class ApplicationBase(BaseModel):
    companyName: str
    jobTitle: str
    jobUrl: Optional[str] = None
    resumeId: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.DRAFT
    notes: Optional[str] = ""


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    companyName: Optional[str] = None
    jobTitle: Optional[str] = None
    jobUrl: Optional[str] = None
    resumeId: Optional[str] = None
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None


class ApplicationResponse(ApplicationBase):
    id: str = Field(alias="_id")
    userId: str
    appliedAt: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

