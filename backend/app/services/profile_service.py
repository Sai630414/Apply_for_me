from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.schemas.profile import calculate_profile_completion


class ProfileService:
    @staticmethod
    def get_default_profile(user_id: str) -> Dict[str, Any]:
        """Generate default empty profile structure."""
        return {
            "userId": user_id,
            "personalInformation": {
                "firstName": "",
                "lastName": "",
                "fullName": "",
                "email": "",
                "phone": "",
                "city": "",
                "state": "",
                "country": "",
                "address": "",
                "dateOfBirth": "",
                "gender": None,
                "linkedin": "",
                "github": "",
                "portfolio": ""
            },
            "education": [],
            "skills": {
                "programmingLanguages": [],
                "frameworks": [],
                "databases": [],
                "cloud": [],
                "cloudPlatforms": [],
                "devops": [],
                "aiMl": [],
                "tools": [],
                "softSkills": [],
                "technicalSkills": []
            },
            "experiences": [],
            "projects": [],
            "professionalLinks": {
                "linkedin": "",
                "github": "",
                "portfolio": ""
            },
            "careerPreferences": {
                "preferredRoles": [],
                "preferredIndustries": [],
                "employmentTypes": [],
                "workModes": [],
                "preferredLocations": [],
                "willingToRelocate": True,
                "availability": "Immediate",
                "careerObjective": "",
                "careerObjectives": "",
                "professionalSummary": "",
                "expectedSalary": "",
                "workAuthorization": "Authorized to work",
                "sponsorshipRequired": False
            },
            "onboardingCompleted": False,
            "completionPercentage": 0,
            "updatedAt": datetime.now(timezone.utc),
            "createdAt": datetime.now(timezone.utc)
        }

    @staticmethod
    async def get_user_profile(user_id: str, db: Optional[Any]) -> Dict[str, Any]:
        """Fetch user profile and calculate completion rate."""
        profile = None
        if db is not None:
            profile = await db.profiles.find_one({"userId": user_id})

        if not profile:
            profile = ProfileService.get_default_profile(user_id)
        else:
            profile["_id"] = str(profile["_id"])
            default = ProfileService.get_default_profile(user_id)
            for k, v in default.items():
                if k not in profile:
                    profile[k] = v
                elif isinstance(v, dict) and isinstance(profile[k], dict):
                    for sub_k, sub_v in v.items():
                        if sub_k not in profile[k]:
                            profile[k][sub_k] = sub_v

        # Harmonize full name
        personal = profile.get("personalInformation", {})
        if not personal.get("fullName") and (personal.get("firstName") or personal.get("lastName")):
            personal["fullName"] = f"{personal.get('firstName', '')} {personal.get('lastName', '')}".strip()

        score, _, _ = calculate_profile_completion(profile)
        profile["completionPercentage"] = score
        return profile

    @staticmethod
    async def create_user_profile(user_id: str, profile_data: Dict[str, Any], db: Optional[Any]) -> Dict[str, Any]:
        """Create new applicant profile. Fails if profile already exists."""
        if db is not None:
            existing = await db.profiles.find_one({"userId": user_id})
            if existing:
                # If already exists, perform update to avoid error
                return await ProfileService.update_user_profile(user_id, profile_data, db)

        now = datetime.now(timezone.utc)
        doc = ProfileService.get_default_profile(user_id)
        
        # Merge input data
        for k in ["personalInformation", "education", "skills", "experiences", "projects", "professionalLinks", "careerPreferences"]:
            if k in profile_data:
                doc[k] = profile_data[k]

        doc["onboardingCompleted"] = profile_data.get("onboardingCompleted", True)
        doc["createdAt"] = now
        doc["updatedAt"] = now

        score, _, _ = calculate_profile_completion(doc)
        doc["completionPercentage"] = score

        if db is not None:
            res = await db.profiles.insert_one(doc)
            doc["_id"] = str(res.inserted_id)
        else:
            doc["_id"] = "dev_profile_101"

        return doc

    @staticmethod
    async def update_user_profile(user_id: str, profile_update: Dict[str, Any], db: Optional[Any]) -> Dict[str, Any]:
        """Complete profile update (PUT / upsert)."""
        now = datetime.now(timezone.utc)
        
        # Harmonize personal information
        personal = profile_update.get("personalInformation", {})
        if not personal.get("fullName") and (personal.get("firstName") or personal.get("lastName")):
            personal["fullName"] = f"{personal.get('firstName', '')} {personal.get('lastName', '')}".strip()
        
        # Ensure backward-compatible mirrors
        skills = profile_update.get("skills", {})
        if "cloud" in skills and "cloudPlatforms" not in skills:
            skills["cloudPlatforms"] = skills["cloud"]
        if "tools" in skills and "technicalSkills" not in skills:
            skills["technicalSkills"] = skills["tools"]

        career = profile_update.get("careerPreferences", {})
        if "careerObjective" in career and "careerObjectives" not in career:
            career["careerObjectives"] = career["careerObjective"]

        doc = {
            "userId": user_id,
            "personalInformation": personal,
            "education": profile_update.get("education", []),
            "skills": skills,
            "experiences": profile_update.get("experiences", []),
            "projects": profile_update.get("projects", []),
            "professionalLinks": profile_update.get("professionalLinks", {}),
            "careerPreferences": career,
            "onboardingCompleted": profile_update.get("onboardingCompleted", True),
            "updatedAt": now
        }

        score, _, _ = calculate_profile_completion(doc)
        doc["completionPercentage"] = score

        if db is not None:
            await db.profiles.update_one(
                {"userId": user_id},
                {"$set": doc},
                upsert=True
            )
            saved = await db.profiles.find_one({"userId": user_id})
            if saved:
                saved["_id"] = str(saved["_id"])
                saved["completionPercentage"] = score
                return saved

        doc["_id"] = "dev_profile_101"
        return doc

    @staticmethod
    async def patch_user_profile(user_id: str, patch_data: Dict[str, Any], db: Optional[Any]) -> Dict[str, Any]:
        """Partial profile update (PATCH) preserving unmodified sections."""
        existing = await ProfileService.get_user_profile(user_id, db)
        now = datetime.now(timezone.utc)

        # Apply provided fields
        for key, val in patch_data.items():
            if val is not None:
                if isinstance(val, dict) and isinstance(existing.get(key), dict):
                    existing[key].update(val)
                else:
                    existing[key] = val

        existing["updatedAt"] = now
        score, _, _ = calculate_profile_completion(existing)
        existing["completionPercentage"] = score

        if db is not None:
            # Drop _id from set dict if present
            set_dict = {k: v for k, v in existing.items() if k != "_id"}
            await db.profiles.update_one(
                {"userId": user_id},
                {"$set": set_dict},
                upsert=True
            )

        return existing

    @staticmethod
    async def get_completion_details(user_id: str, db: Optional[Any]) -> Dict[str, Any]:
        """Get completion score and actionable suggestions."""
        profile = None
        has_profile = False
        if db is not None:
            profile = await db.profiles.find_one({"userId": user_id})
            if profile:
                has_profile = True

        if not profile:
            profile = ProfileService.get_default_profile(user_id)

        score, missing, suggestions = calculate_profile_completion(profile)
        return {
            "completionPercentage": score,
            "missingRequired": missing,
            "suggestions": suggestions,
            "hasProfile": has_profile and profile.get("onboardingCompleted", False)
        }
