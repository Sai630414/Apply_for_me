from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FormFieldDescriptor(BaseModel):
    elementId: Optional[str] = None
    name: Optional[str] = None
    selector: Optional[str] = None
    type: str = "text"
    label: Optional[str] = None
    placeholder: Optional[str] = None
    ariaLabel: Optional[str] = None
    autocomplete: Optional[str] = None
    options: Optional[List[str]] = Field(default_factory=list)
    currentValue: Optional[str] = None


class FormMappingRequest(BaseModel):
    url: Optional[str] = None
    formTitle: Optional[str] = None
    companyName: Optional[str] = None
    jobTitle: Optional[str] = None
    jobDescription: Optional[str] = None
    fields: List[FormFieldDescriptor]


class FormFieldMapping(BaseModel):
    elementIdentifier: str  # id, name, or selector
    fieldName: Optional[str] = None  # user-facing label or name
    selector: Optional[str] = None
    profileKey: Optional[str] = None
    fillValue: Optional[Any] = None
    confidence: float = 0.0
    requiresReview: bool = False
    reason: Optional[str] = None
    category: str = "DIRECT_PROFILE_MAPPING"  # DIRECT_PROFILE_MAPPING | AI_GENERATED_ANSWER | USER_CONFIRMATION_REQUIRED | FILE_UPLOAD | CONSENT_OR_LEGAL | UNSUPPORTED_FIELD
    fieldType: Optional[str] = "text"
    options: Optional[List[str]] = Field(default_factory=list)
    suggestedOptions: Optional[List[str]] = Field(default_factory=list)
    questionId: Optional[str] = None
    questionCategory: Optional[str] = None
    status: Optional[str] = None

    # Section 12 structured fields
    field_id: Optional[str] = None
    question: Optional[str] = None
    proposed_answer: Optional[Any] = None
    requires_confirmation: bool = False
    confirmation_reason: Optional[str] = None
    filled: bool = False
    validation_notes: Optional[List[str]] = Field(default_factory=list)


class FormMappingResponse(BaseModel):
    mappings: List[FormFieldMapping]
    totalFields: int
    matchedFields: int
    unmatchedFields: int
    directMappedCount: int = 0
    aiGeneratedCount: int = 0
    userInputRequiredCount: int = 0  # alias for userConfirmationRequiredCount
    userConfirmationRequiredCount: int = 0
    fileUploadCount: int = 0
    consentLegalCount: int = 0
    unsupportedCount: int = 0
