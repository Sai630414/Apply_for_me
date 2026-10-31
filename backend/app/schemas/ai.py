from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnswerGenerationRequest(BaseModel):
    question: str
    companyName: str
    jobTitle: str
    jobDescription: Optional[str] = ""
    mode: Optional[str] = "standard"  # standard, concise, professional, technical


class AnswerGenerationResponse(BaseModel):
    question: str
    companyName: str
    jobTitle: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.95)
    keyPointsUsed: List[str] = Field(default_factory=list)
    clarificationNeeded: Optional[str] = None


class FieldClassificationRequest(BaseModel):
    fieldName: str
    fieldLabel: Optional[str] = ""
    placeholder: Optional[str] = ""
    fieldType: Optional[str] = "text"
    options: Optional[List[str]] = Field(default_factory=list)


class FieldClassificationResponse(BaseModel):
    mappedPath: Optional[str] = None  # e.g. "personalInformation.email"
    confidence: float = 0.0
    fieldCategory: str = "unknown"
    suggestedFormat: Optional[str] = None


class JobAnalysisRequest(BaseModel):
    jobTitle: str
    companyName: str
    jobDescription: str


class JobAnalysisResponse(BaseModel):
    detectedSkills: List[str] = Field(default_factory=list)
    matchingSkills: List[str] = Field(default_factory=list)
    missingSkills: List[str] = Field(default_factory=list)
    matchScore: int = 0
    roleSummary: str = ""

