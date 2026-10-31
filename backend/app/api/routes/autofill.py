from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.schemas.autofill import FormMappingRequest, FormMappingResponse
from app.services.profile_service import ProfileService
from app.services.field_mapping_service import FieldMappingService

router = APIRouter(prefix="/autofill", tags=["Autofill & Field Mapping"])


@router.post("/map-fields", response_model=FormMappingResponse)
async def map_form_fields(
    payload: FormMappingRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Intelligently map detected webpage form fields:
    - Direct profile fields (deterministic & instant)
    - Dropdowns with option matching
    - AI-tailored grounded answers for open-ended questions using Ollama & LangChain
    - Categorization: DIRECT_PROFILE_FIELD, AI_GENERATED_ANSWER, USER_INPUT_REQUIRED, FILE_UPLOAD, CONSENT_OR_LEGAL, UNSUPPORTED
    """
    user_id = str(current_user["_id"])
    profile = await ProfileService.get_user_profile(user_id, db)
    return await FieldMappingService.map_entire_form_async(
        fields=payload.fields,
        profile=profile,
        company_name=payload.companyName or "",
        job_title=payload.jobTitle or "",
        job_description=payload.jobDescription or ""
    )

