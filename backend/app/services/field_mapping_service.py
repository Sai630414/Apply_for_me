import re
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.autofill import FormFieldDescriptor, FormFieldMapping, FormMappingResponse
from app.core.config import settings
from app.services.ai_answer_service import (
    generate_answer,
    generate_application_answer,
    classify_question_category,
    _generate_deterministic_answer
)

logger = logging.getLogger("applyforme.mapping")

# Valid direct profile keys
ALLOWED_PROFILE_KEYS = {
    "personalInformation.firstName",
    "personalInformation.lastName",
    "personalInformation.fullName",
    "personalInformation.email",
    "personalInformation.phone",
    "personalInformation.city",
    "personalInformation.state",
    "personalInformation.country",
    "personalInformation.address",
    "personalInformation.dateOfBirth",
    "personalInformation.gender",
    "education.institution",
    "education.college",
    "education.degree",
    "education.specialization",
    "education.branch",
    "education.graduationYear",
    "education.cgpa",
    "skills.all",
    "skills.programmingLanguages",
    "skills.frameworks",
    "skills.technicalSkills",
    "professionalLinks.linkedin",
    "professionalLinks.github",
    "professionalLinks.portfolio",
    "experiences.currentCompany",
    "experiences.currentRole",
    "careerPreferences.professionalSummary",
    "careerPreferences.careerObjective",
    "careerPreferences.availability",
    "careerPreferences.workAuthorization",
    "careerPreferences.willingToRelocate",
    "careerPreferences.sponsorshipRequired",
    "careerPreferences.expectedSalary",
}


def match_select_option(target_value: Any, options: List[str]) -> Optional[str]:
    """
    Intelligently and safely match a target value against available HTML select options.
    Returns the exact matching option string from options list, or None.
    """
    if target_value is None or not options:
        return None

    target_str = str(target_value).strip().lower()
    if not target_str:
        return None

    # 1. Exact case-insensitive match
    for opt in options:
        if opt.strip().lower() == target_str:
            return opt

    # 2. Boolean synonyms
    bool_yes = {"true", "yes", "authorized", "1", "y", "eligible", "will", "authorized to work"}
    bool_no = {"false", "no", "not authorized", "0", "n", "ineligible", "will not", "unauthorized"}
    
    is_target_yes = target_str in bool_yes or any(target_str.startswith(w) for w in ["authorized", "eligible", "yes", "authorized to work"])
    is_target_no = target_str in bool_no or any(target_str.startswith(w) for w in ["not authorized", "ineligible", "no", "unauthorized", "not"])

    if is_target_yes:
        for opt in options:
            if opt.strip().lower() in bool_yes:
                return opt
    elif is_target_no:
        for opt in options:
            if opt.strip().lower() in bool_no:
                return opt

    # 3. Country / Location synonyms
    geo_map = {
        "usa": ["united states", "united states of america", "us", "u.s.", "u.s.a."],
        "united states": ["usa", "us", "united states of america", "u.s."],
        "india": ["ind", "in"],
        "san francisco": ["sf", "san francisco, ca", "san francisco bay area", "bay area"],
    }
    synonyms = geo_map.get(target_str, [])
    for opt in options:
        opt_lower = opt.strip().lower()
        if opt_lower in synonyms or any(s in opt_lower for s in synonyms):
            return opt

    # 4. Degree matching
    deg_map = {
        "b.s.": ["bachelor", "bachelor of science", "bs", "undergraduate"],
        "b.tech": ["bachelor of technology", "btech", "b.e.", "bachelor of engineering", "undergraduate"],
        "m.s.": ["master of science", "ms", "master", "postgraduate"],
        "m.tech": ["master of technology", "mtech", "master"]
    }
    deg_synonyms = deg_map.get(target_str, [])
    for opt in options:
        opt_lower = opt.strip().lower()
        if any(s in opt_lower for s in deg_synonyms):
            return opt

    # 5. Substring match (e.g. target "2025" in "2025 (Expected)")
    for opt in options:
        opt_lower = opt.strip().lower()
        if target_str in opt_lower or (len(opt_lower) >= 3 and opt_lower in target_str):
            if len(target_str) >= 2 and len(opt_lower) >= 2:
                return opt

    return None


class FieldMappingService:
    # Deterministic mapping rules ordered from most specific to general
    # Format: (Regex pattern, Profile key path, Confidence score, Field description)
    RULE_PATTERNS = [
        # First Name (exclude last name / full name)
        (r"(?i)\b(first[\s_-]?name|given[\s_-]?name|fname|forename)\b", "personalInformation.firstName", 0.99, "First Name"),
        # Last Name (exclude first name / full name)
        (r"(?i)\b(last[\s_-]?name|family[\s_-]?name|surname|lname)\b", "personalInformation.lastName", 0.99, "Last Name"),
        # Full Name (make sure not to match company name, school name, file name)
        (r"(?i)(?<!company[\s_])(?<!school[\s_])(?<!file[\s_])\b(full[\s_-]?name|your[\s_-]?name|applicant[\s_-]?name|candidate[\s_-]?name)\b", "personalInformation.fullName", 0.96, "Full Name"),
        # Standalone name
        (r"(?i)^(name|applicant|candidate)$", "personalInformation.fullName", 0.92, "Full Name"),

        # Email
        (r"(?i)\b(e[\s_-]?mail|email[\s_-]?address)\b", "personalInformation.email", 0.99, "Email Address"),

        # Phone
        (r"(?i)\b(phone|mobile|cell|contact[\s_-]?number|telephone|phone[\s_-]?number)\b", "personalInformation.phone", 0.98, "Phone Number"),

        # Date of birth
        (r"(?i)\b(birth[\s_-]?date|dob|date[\s_-]?of[\s_-]?birth|birth[\s_-]?day)\b", "personalInformation.dateOfBirth", 0.96, "Date of Birth"),

        # Gender
        (r"(?i)\b(gender|sex)\b", "personalInformation.gender", 0.94, "Gender"),

        # Address & Location
        (r"(?i)\b(street[\s_-]?address|home[\s_-]?address|address[\s_-]?line|residential[\s_-]?address)\b", "personalInformation.address", 0.95, "Street Address"),
        (r"(?i)\b(city|town|municipality)\b", "personalInformation.city", 0.95, "City"),
        (r"(?i)\b(state|province|region)\b", "personalInformation.state", 0.94, "State/Province"),
        (r"(?i)\b(country|nation)\b", "personalInformation.country", 0.95, "Country"),
        (r"(?i)\b(current[\s_-]?location|present[\s_-]?location|where[\s_-]?are[\s_-]?you[\s_-]?located|location)\b", "personalInformation.city", 0.91, "Current Location"),

        # Education
        (r"(?i)\b(university|college|institution|school[\s_-]?name|alma[\s_-]?mater)\b", "education.institution", 0.95, "University/College"),
        (r"(?i)\b(degree|qualification|program|level[\s_-]?of[\s_-]?education)\b", "education.degree", 0.94, "Degree"),
        (r"(?i)\b(branch|specialization|major|field[\s_-]?of[\s_-]?study|stream|department)\b", "education.specialization", 0.93, "Major/Branch"),
        (r"(?i)\b(grad(uation)?[\s_-]?year|passing[\s_-]?year|completion[\s_-]?year|year[\s_-]?of[\s_-]?graduation)\b", "education.graduationYear", 0.96, "Graduation Year"),
        (r"(?i)\b(cgpa|gpa|percentage|academic[\s_-]?score|marks|grade[\s_-]?point)\b", "education.cgpa", 0.95, "CGPA/GPA"),

        # Skills & Technical Stack
        (r"(?i)\b(skills|technical[\s_-]?skills|key[\s_-]?skills|programming[\s_-]?languages|tech[\s_-]?stack|technologies)\b", "skills.all", 0.96, "Skills"),

        # Professional Links
        (r"(?i)\b(linkedin|linked[\s_-]?in|linkedin[\s_-]?profile|linkedin[\s_-]?url)\b", "professionalLinks.linkedin", 0.99, "LinkedIn URL"),
        (r"(?i)\b(github|git[\s_-]?hub|github[\s_-]?profile|github[\s_-]?url)\b", "professionalLinks.github", 0.99, "GitHub URL"),
        (r"(?i)\b(portfolio|personal[\s_-]?website|personal[\s_-]?url|website[\s_-]?url)\b", "professionalLinks.portfolio", 0.96, "Portfolio URL"),

        # Work Preferences & Eligibility
        (r"(?i)\b(authorized[\s_-]?to[\s_-]?work|legally[\s_-]?authorized|work[\s_-]?authoriz(ed|ation)|legal[\s_-]?right[\s_-]?to[\s_-]?work)\b", "careerPreferences.workAuthorization", 0.93, "Work Authorization"),
        (r"(?i)\b(sponsorship|require[\s_-]?visa|visa[\s_-]?sponsorship|need[\s_-]?sponsorship)\b", "careerPreferences.sponsorshipRequired", 0.93, "Visa Sponsorship"),
        (r"(?i)\b(willing[\s_-]?to[\s_-]?relocate|relocat(e|ion))\b", "careerPreferences.willingToRelocate", 0.92, "Relocation"),
        (r"(?i)\b(availability|notice[\s_-]?period|when[\s_-]?can[\s_-]?you[\s_-]?start|start[\s_-]?date)\b", "careerPreferences.availability", 0.90, "Availability"),
        (r"(?i)\b(expected[\s_-]?salary|compensation[\s_-]?expectation|desired[\s_-]?salary)\b", "careerPreferences.expectedSalary", 0.90, "Expected Salary"),

        # Current Company / Role
        (r"(?i)\b(current[\s_-]?company|present[\s_-]?company|current[\s_-]?employer)\b", "experiences.currentCompany", 0.90, "Current Company"),
        (r"(?i)\b(current[\s_-]?role|current[\s_-]?title|current[\s_-]?designation)\b", "experiences.currentRole", 0.90, "Current Role"),
    ]

    @classmethod
    def get_nested_value(cls, data: dict, path: str) -> Any:
        """Retrieve nested dictionary value using dot notation, with aliases and list fallbacks."""
        if not data:
            return None

        # Special handler for skills.all
        if path == "skills.all":
            skills_dict = data.get("skills", {})
            all_skills = []
            for category in [
                "programmingLanguages",
                "frameworks",
                "databases",
                "cloud",
                "cloudPlatforms",
                "devops",
                "tools",
                "technicalSkills"
            ]:
                items = skills_dict.get(category, [])
                if isinstance(items, list):
                    for item in items:
                        if item and item not in all_skills:
                            all_skills.append(item)
            return ", ".join(all_skills) if all_skills else None

        # Special handler for education items
        if path.startswith("education."):
            attr = path.split(".", 1)[1]
            edu_list = data.get("education", [])
            if edu_list and isinstance(edu_list, list) and len(edu_list) > 0:
                first = edu_list[0]
                if attr in ("institution", "college"):
                    return first.get("institution") or first.get("college")
                if attr in ("specialization", "branch"):
                    return first.get("specialization") or first.get("branch")
                return first.get(attr)
            return None

        # Special handler for experiences
        if path == "experiences.currentCompany":
            experiences = data.get("experiences", [])
            for exp in experiences:
                if exp.get("currentlyWorking"):
                    return exp.get("company")
            return experiences[0].get("company") if experiences else None

        if path == "experiences.currentRole":
            experiences = data.get("experiences", [])
            for exp in experiences:
                if exp.get("currentlyWorking"):
                    return exp.get("role") or exp.get("title")
            return (experiences[0].get("role") or experiences[0].get("title")) if experiences else None

        # Special handler for full name / first name / last name
        if path == "personalInformation.fullName":
            personal = data.get("personalInformation", {})
            if personal.get("fullName"):
                return personal["fullName"]
            first = personal.get("firstName", "")
            last = personal.get("lastName", "")
            full = f"{first} {last}".strip()
            return full or None

        if path == "personalInformation.firstName":
            personal = data.get("personalInformation", {})
            if personal.get("firstName"):
                return personal["firstName"]
            full = personal.get("fullName", "")
            return full.split()[0] if full else None

        if path == "personalInformation.lastName":
            personal = data.get("personalInformation", {})
            if personal.get("lastName"):
                return personal["lastName"]
            full = personal.get("fullName", "")
            parts = full.split()
            return " ".join(parts[1:]) if len(parts) > 1 else None

        # Special handler for professional links
        if path in ("professionalLinks.linkedin", "personalInformation.linkedin"):
            return (
                data.get("professionalLinks", {}).get("linkedin")
                or data.get("personalInformation", {}).get("linkedin")
            )

        if path in ("professionalLinks.github", "personalInformation.github"):
            return (
                data.get("professionalLinks", {}).get("github")
                or data.get("personalInformation", {}).get("github")
            )

        if path in ("professionalLinks.portfolio", "personalInformation.portfolio"):
            return (
                data.get("professionalLinks", {}).get("portfolio")
                or data.get("personalInformation", {}).get("portfolio")
            )

        # Boolean conversions
        if path == "careerPreferences.willingToRelocate":
            val = data.get("careerPreferences", {}).get("willingToRelocate")
            return "Yes" if val else "No"

        if path == "careerPreferences.sponsorshipRequired":
            val = data.get("careerPreferences", {}).get("sponsorshipRequired")
            return "No" if (val is False) else ("Yes" if val else "No")

        if path == "careerPreferences.workAuthorization":
            val = data.get("careerPreferences", {}).get("workAuthorization")
            return val or "Yes"

        # Standard dot notation traversal
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    @classmethod
    def is_ai_question(cls, field: FormFieldDescriptor) -> bool:
        """Identify open-ended questions suited for AI answer generation."""
        text = " ".join(filter(None, [field.label, field.name, field.placeholder, field.elementId])).lower()

        # If it contains open-ended question triggers, it is an AI question
        question_triggers = [
            "why do you want", "why are you interested", "why join", "why work at", "why this company",
            "why should we hire", "why us", "tell us about yourself", "about you",
            "describe your", "describe a project", "describe an experience", "technical experience",
            "describe a", "tell us about", "what are your", "what makes you", "core strengths",
            "career goals", "where do you see yourself", "explain your", "cover letter",
            "what excites you", "share a project", "challenging project",
            "available for", "3 months internship", "3-month internship", "internship duration",
            "prior recruitment", "recruitment internship", "prior experience", "previous experience",
            "unpaid internship", "comfortable for an unpaid", "comfortable with an unpaid",
            "join us immediately", "can you join us", "can you join immediately"
        ]
        if any(trigger in text for trigger in question_triggers):
            return True

        # Pure skill lists and addresses are direct profile fields, not subjective questions
        if re.search(r"\b(technical[\s_-]?skills|key[\s_-]?skills|programming[\s_-]?languages)\b", text) and not any(w in text for w in ["why", "describe", "explain"]):
            return False
        if re.search(r"\b(street[\s_-]?address|home[\s_-]?address|residential[\s_-]?address|address[\s_-]?line)\b", text):
            return False

        if field.type == "textarea":
            return True

        return False

    @classmethod
    def is_consent_or_legal(cls, field: FormFieldDescriptor) -> bool:
        """Identify legal declarations, privacy policies, or consent checkboxes."""
        text = " ".join(filter(None, [field.label, field.name, field.placeholder, field.elementId])).lower()
        legal_keywords = [
            "privacy policy", "terms of service", "terms and conditions", "terms & conditions",
            "i agree", "i acknowledge", "i certify", "i declare", "under penalty of perjury",
            "truthful and accurate", "background check consent", "equal opportunity",
            "voluntary self-identification", "veteran status", "disability status",
            "consent to store", "legal declaration", "code of conduct"
        ]
        if field.type == "checkbox" and any(k in text for k in legal_keywords):
            return True
        if any(k in text for k in ["i certify that", "under penalty of perjury", "terms & conditions", "i agree to the"]):
            return True
        return False

    @classmethod
    def is_file_upload(cls, field: FormFieldDescriptor) -> bool:
        """Identify resume, CV, or document upload fields."""
        if field.type == "file":
            return True
        text = " ".join(filter(None, [field.label, field.name, field.placeholder, field.elementId])).lower()
        return any(k in text for k in ["upload resume", "upload cv", "attach resume", "attach cv", "resume/cv", "cover letter file", "transcript file"])

    @classmethod
    def is_user_input_required(cls, field: FormFieldDescriptor, profile: dict) -> Tuple[bool, Optional[str]]:
        """Determine if a factual field has missing data in the profile and requires user input."""
        text = " ".join(filter(None, [field.label, field.name, field.placeholder, field.elementId])).lower()

        # Notice period
        if any(k in text for k in ["notice period", "days of notice"]):
            val = profile.get("careerPreferences", {}).get("availability")
            if not val:
                return True, "Notice period not specified in applicant profile"

        # Expected salary
        if any(k in text for k in ["expected salary", "salary expectation", "compensation expectation"]):
            val = profile.get("careerPreferences", {}).get("expectedSalary")
            if not val:
                return True, "Expected salary not specified in applicant profile"

        # Current company when no current experience
        if any(k in text for k in ["current company", "current employer"]):
            experiences = profile.get("experiences", [])
            has_current = any(e.get("currentlyWorking") for e in experiences)
            if not has_current and not experiences:
                return True, "No current employer found in applicant profile"

        # Security clearance / driver's license
        if any(k in text for k in ["security clearance", "clearance level", "driver's license", "passport number"]):
            return True, "Personal factual credential missing from profile"

        return False, None

    @classmethod
    def classify_and_map_field(cls, field: FormFieldDescriptor, profile: dict) -> FormFieldMapping:
        """
        Classify a single form input into one of the 6 core categories:
        1. FILE_UPLOAD
        2. CONSENT_OR_LEGAL
        3. USER_INPUT_REQUIRED
        4. AI_GENERATED_ANSWER
        5. DIRECT_PROFILE_FIELD
        6. UNSUPPORTED
        """
        element_id = field.selector or field.elementId or field.name or "unknown"
        field_label = field.label or field.placeholder or field.name or "Field"
        options = field.options or []

        # 1. File Upload
        if cls.is_file_upload(field):
            return FormFieldMapping(
                elementIdentifier=element_id,
                fieldName=field_label,
                selector=field.selector,
                profileKey=None,
                fillValue=None,
                confidence=0.98,
                requiresReview=True,
                reason="File upload requires explicit user file selection due to browser security restrictions",
                category="FILE_UPLOAD",
                fieldType="file",
                options=options
            )

        # 2. Consent / Legal Declaration
        if cls.is_consent_or_legal(field):
            return FormFieldMapping(
                elementIdentifier=element_id,
                fieldName=field_label,
                selector=field.selector,
                profileKey=None,
                fillValue=None,
                confidence=0.95,
                requiresReview=True,
                reason="Legal declarations and consent checkboxes must never be accepted automatically",
                category="CONSENT_OR_LEGAL",
                fieldType=field.type,
                options=options
            )

        # 3. User Input Required (Factual details missing from profile)
        needs_input, input_reason = cls.is_user_input_required(field, profile)
        if needs_input:
            return FormFieldMapping(
                elementIdentifier=element_id,
                fieldName=field_label,
                selector=field.selector,
                profileKey=None,
                fillValue=None,
                confidence=0.90,
                requiresReview=True,
                reason=input_reason or "Factual information missing from applicant profile",
                category="USER_INPUT_REQUIRED",
                fieldType=field.type,
                options=options
            )

        # 4. Open-ended / application question for AI generation
        if cls.is_ai_question(field):
            q_cat = classify_question_category(field_label, field.type)

            # If it's an unpaid internship question and applicant profile has no approval, require user input
            if q_cat == "COMPENSATION_PREFERENCE" or "unpaid" in field_label.lower():
                accept_unpaid = profile.get("careerPreferences", {}).get("acceptUnpaid")
                if not accept_unpaid:
                    return FormFieldMapping(
                        elementIdentifier=element_id,
                        fieldName=field_label,
                        selector=field.selector,
                        profileKey=None,
                        fillValue=None,
                        confidence=0.0,
                        requiresReview=True,
                        reason="Personal preference regarding unpaid internships is not specified in profile. Manual user input required.",
                        category="USER_INPUT_REQUIRED",
                        fieldType=field.type,
                        options=options,
                        questionId=element_id,
                        questionCategory="COMPENSATION_PREFERENCE",
                        status="needs_user_input"
                    )

            return FormFieldMapping(
                elementIdentifier=element_id,
                fieldName=field_label,
                selector=field.selector,
                profileKey="ai_generated",
                fillValue=None,  # Will be populated during async generation
                confidence=0.92,
                requiresReview=True,
                reason=f"Application question ({q_cat}) suitable for tailored response",
                category="AI_GENERATED_ANSWER",
                fieldType=field.type,
                options=options,
                questionId=element_id,
                questionCategory=q_cat,
                status="needs_user_input"
            )

        # 5. Direct Autocomplete Attribute Matching
        auto = (field.autocomplete or "").lower()
        if auto:
            if "given-name" in auto:
                val = cls.get_nested_value(profile, "personalInformation.firstName")
                return FormFieldMapping(elementIdentifier=element_id, fieldName="First Name", selector=field.selector, profileKey="personalInformation.firstName", fillValue=val, confidence=0.99, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)
            if "family-name" in auto:
                val = cls.get_nested_value(profile, "personalInformation.lastName")
                return FormFieldMapping(elementIdentifier=element_id, fieldName="Last Name", selector=field.selector, profileKey="personalInformation.lastName", fillValue=val, confidence=0.99, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)
            if auto in ("name", "full-name"):
                val = cls.get_nested_value(profile, "personalInformation.fullName")
                return FormFieldMapping(elementIdentifier=element_id, fieldName="Full Name", selector=field.selector, profileKey="personalInformation.fullName", fillValue=val, confidence=0.98, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)
            if "email" in auto:
                val = cls.get_nested_value(profile, "personalInformation.email")
                return FormFieldMapping(elementIdentifier=element_id, fieldName="Email Address", selector=field.selector, profileKey="personalInformation.email", fillValue=val, confidence=0.99, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)
            if "tel" in auto:
                val = cls.get_nested_value(profile, "personalInformation.phone")
                return FormFieldMapping(elementIdentifier=element_id, fieldName="Phone Number", selector=field.selector, profileKey="personalInformation.phone", fillValue=val, confidence=0.98, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)

        # HTML Input Type Specifics
        if field.type == "email":
            val = cls.get_nested_value(profile, "personalInformation.email")
            return FormFieldMapping(elementIdentifier=element_id, fieldName="Email Address", selector=field.selector, profileKey="personalInformation.email", fillValue=val, confidence=0.99, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)

        if field.type == "tel":
            val = cls.get_nested_value(profile, "personalInformation.phone")
            return FormFieldMapping(elementIdentifier=element_id, fieldName="Phone Number", selector=field.selector, profileKey="personalInformation.phone", fillValue=val, confidence=0.98, requiresReview=False, category="DIRECT_PROFILE_FIELD", fieldType=field.type, options=options)

        # 6. Regex Heuristic Rules for Direct Profile Fields
        combined_text = " ".join(filter(None, [
            field.name,
            field.elementId,
            field.label,
            field.placeholder,
            field.ariaLabel,
            field.autocomplete
        ])).lower()

        for pattern, profile_path, confidence, name_desc in cls.RULE_PATTERNS:
            if re.search(pattern, combined_text):
                val = cls.get_nested_value(profile, profile_path)

                # If this is a select field with options, match against options
                if field.type == "select" and options:
                    matched_opt = match_select_option(val, options)
                    if matched_opt:
                        return FormFieldMapping(
                            elementIdentifier=element_id,
                            fieldName=name_desc,
                            selector=field.selector,
                            profileKey=profile_path,
                            fillValue=matched_opt,
                            confidence=confidence,
                            requiresReview=False,
                            category="DIRECT_PROFILE_FIELD",
                            fieldType=field.type,
                            options=options
                        )
                    else:
                        return FormFieldMapping(
                            elementIdentifier=element_id,
                            fieldName=name_desc,
                            selector=field.selector,
                            profileKey=profile_path,
                            fillValue=None,
                            confidence=0.60,
                            requiresReview=True,
                            reason=f"No matching option in dropdown for profile value '{val}'",
                            category="USER_INPUT_REQUIRED",
                            fieldType=field.type,
                            options=options
                        )

                # Radio button handling
                if field.type == "radio" and options:
                    matched_radio = match_select_option(val, options)
                    return FormFieldMapping(
                        elementIdentifier=element_id,
                        fieldName=name_desc,
                        selector=field.selector,
                        profileKey=profile_path,
                        fillValue=matched_radio or val,
                        confidence=confidence,
                        requiresReview=not bool(matched_radio),
                        category="DIRECT_PROFILE_FIELD",
                        fieldType=field.type,
                        options=options
                    )

                return FormFieldMapping(
                    elementIdentifier=element_id,
                    fieldName=name_desc,
                    selector=field.selector,
                    profileKey=profile_path,
                    fillValue=val,
                    confidence=confidence,
                    requiresReview=confidence < 0.85 or val is None,
                    category="DIRECT_PROFILE_FIELD",
                    fieldType=field.type,
                    options=options
                )

        # 7. Fallback for completely unrecognized field
        return FormFieldMapping(
            elementIdentifier=element_id,
            fieldName=field_label,
            selector=field.selector,
            profileKey=None,
            fillValue=None,
            confidence=0.0,
            requiresReview=True,
            reason="Unrecognized field - requires manual input",
            category="UNSUPPORTED",
            fieldType=field.type,
            options=options
        )

    @classmethod
    async def map_entire_form_async(
        cls,
        fields: List[FormFieldDescriptor],
        profile: dict,
        company_name: str = "",
        job_title: str = "",
        job_description: str = ""
    ) -> FormMappingResponse:
        """
        Classifies all detected fields and generates question-specific answers concurrently.
        Guarantees independent question classification, profile grounding, and safeguards against answer reuse.
        """
        mappings: List[FormFieldMapping] = []
        ai_tasks = []
        ai_indices = []

        direct_count = 0
        ai_count = 0
        user_input_count = 0
        file_count = 0
        consent_count = 0
        unsupported_count = 0
        matched = 0

        # Pass 1: Deterministic classification of all fields
        for idx, f in enumerate(fields):
            mapping = cls.classify_and_map_field(f, profile)
            mappings.append(mapping)

            if mapping.category == "AI_GENERATED_ANSWER":
                ai_indices.append(idx)
                q_text = f.label or f.placeholder or f.name or "Application question"
                qid = f.elementId or f.name or f"field_{idx}"
                ai_tasks.append(
                    generate_answer(
                        question_id=qid,
                        question_text=q_text,
                        field_type=f.type,
                        applicant_profile=profile,
                        company_name=company_name,
                        job_title=job_title,
                        job_description=job_description
                    )
                )

        # Pass 2: Concurrent AI answer generation with controlled concurrency & anti-reuse safeguards
        if ai_tasks:
            concurrency_limit = getattr(settings, "LLM_CONCURRENCY", 1)
            semaphore = asyncio.Semaphore(concurrency_limit)

            async def bounded_task(task_coro):
                async with semaphore:
                    return await task_coro

            batch_timeout = max(180.0, len(ai_tasks) * 60.0)
            try:
                ai_results = await asyncio.wait_for(
                    asyncio.gather(*(bounded_task(t) for t in ai_tasks), return_exceptions=True),
                    timeout=batch_timeout
                )
                seen_answers: Dict[str, Tuple[str, str]] = {}  # answer_str -> (question_id, category)

                for idx, res in zip(ai_indices, ai_results):
                    f = fields[idx]
                    qid = f.elementId or f.name or f"field_{idx}"
                    q_text = f.label or f.placeholder or f.name or "Application question"

                    if isinstance(res, Exception):
                        logger.warning(f"AI generation task for {qid} failed: {res}. Using deterministic fallback.")
                        res = _generate_deterministic_answer(
                            question_id=qid,
                            question_text=q_text,
                            category=classify_question_category(q_text, f.type),
                            profile=profile,
                            company_name=company_name,
                            job_title=job_title,
                            job_description=job_description
                        )

                    # Anti-reuse safeguard: detect duplicate answers across different categories
                    if hasattr(res, "answer") and res.answer:
                        ans_key = res.answer.strip()
                        if ans_key in seen_answers:
                            prev_qid, prev_cat = seen_answers[ans_key]
                            if prev_cat != res.category:
                                logger.warning(
                                    f"[Anti-Reuse] Detected identical answer across categories '{prev_cat}' ({prev_qid}) "
                                    f"and '{res.category}' ({qid}). Generating question-specific answer."
                                )
                                res = _generate_deterministic_answer(
                                    question_id=qid,
                                    question_text=q_text,
                                    category=classify_question_category(q_text, f.type),
                                    profile=profile,
                                    company_name=company_name,
                                    job_title=job_title,
                                    job_description=job_description
                                )
                        seen_answers[ans_key] = (qid, getattr(res, "category", "OTHER"))

                    if hasattr(res, "status") and res.status == "generated" and res.answer:
                        mappings[idx].fillValue = res.answer
                        mappings[idx].confidence = res.confidence
                        mappings[idx].reason = res.reason or "Tailored answer grounded in profile"
                        mappings[idx].questionCategory = res.category
                        mappings[idx].status = "generated"
                        mappings[idx].requiresReview = False
                        mappings[idx].category = "AI_GENERATED_ANSWER"
                    elif hasattr(res, "status") and res.status in ("needs_user_input", "error"):
                        mappings[idx].fillValue = None
                        mappings[idx].confidence = 0.0
                        mappings[idx].reason = res.reason or "Specific information missing from profile"
                        mappings[idx].questionCategory = res.category
                        mappings[idx].status = res.status
                        mappings[idx].category = "USER_INPUT_REQUIRED"
                        mappings[idx].requiresReview = True

            except asyncio.TimeoutError:
                logger.warning("AI answer generation batch timed out. Applying deterministic category generators.")
                for idx in ai_indices:
                    if not mappings[idx].fillValue:
                        f = fields[idx]
                        qid = f.elementId or f.name or f"field_{idx}"
                        q_text = f.label or f.placeholder or f.name or "Application question"
                        q_cat = classify_question_category(q_text, f.type)
                        fb = _generate_deterministic_answer(
                            question_id=qid,
                            question_text=q_text,
                            category=q_cat,
                            profile=profile,
                            company_name=company_name,
                            job_title=job_title,
                            job_description=job_description
                        )
                        if fb.status == "generated" and fb.answer:
                            mappings[idx].fillValue = fb.answer
                            mappings[idx].confidence = fb.confidence
                            mappings[idx].reason = fb.reason
                            mappings[idx].questionCategory = fb.category
                            mappings[idx].status = "generated"
                            mappings[idx].requiresReview = False
                            mappings[idx].category = "AI_GENERATED_ANSWER"
                        else:
                            mappings[idx].fillValue = None
                            mappings[idx].confidence = 0.0
                            mappings[idx].reason = fb.reason
                            mappings[idx].questionCategory = fb.category
                            mappings[idx].status = "needs_user_input"
                            mappings[idx].category = "USER_INPUT_REQUIRED"
                            mappings[idx].requiresReview = True

        # Pass 3: Calculate accurate category statistics and populate structured fields
        for m in mappings:
            # Section 12 structured fields
            m.field_id = m.elementIdentifier
            m.question = m.fieldName or m.elementIdentifier
            m.questionId = m.elementIdentifier
            m.filled = False

            if m.category in ("USER_INPUT_REQUIRED", "USER_CONFIRMATION_REQUIRED", "UNSUPPORTED", "UNSUPPORTED_FIELD"):
                m.requiresReview = True
                m.requires_confirmation = True
                m.status = m.status or "needs_user_input"
                if not m.fillValue:
                    prop_ans, conf_reason = cls._generate_proposed_answer_for_missing_field(m, profile)
                    m.proposed_answer = prop_ans
                    m.confirmation_reason = conf_reason or m.reason or "Information not found in applicant profile."
                else:
                    m.proposed_answer = m.fillValue
                    m.confirmation_reason = m.reason
            elif m.category == "CONSENT_OR_LEGAL":
                m.requiresReview = True
                m.requires_confirmation = True
                m.proposed_answer = "[Manual review & confirmation required for legal declaration]"
                m.confirmation_reason = "Legal declarations, privacy consents, and accuracy certifications must be manually accepted by the applicant."
            elif m.category == "FILE_UPLOAD":
                m.requiresReview = True
                m.requires_confirmation = True
                m.proposed_answer = "[Select resume file from profile]"
                m.confirmation_reason = "Browser security restrictions require manual resume document selection."
            else:
                m.proposed_answer = m.fillValue
                m.requires_confirmation = m.requiresReview
                m.confirmation_reason = m.reason if m.requiresReview else None

            if m.category == "DIRECT_PROFILE_FIELD":
                direct_count += 1
                if m.fillValue is not None and m.fillValue != "":
                    matched += 1
            elif m.category == "AI_GENERATED_ANSWER":
                ai_count += 1
                if m.fillValue is not None and m.fillValue != "":
                    matched += 1
            elif m.category in ("USER_INPUT_REQUIRED", "USER_CONFIRMATION_REQUIRED"):
                user_input_count += 1
            elif m.category == "FILE_UPLOAD":
                file_count += 1
            elif m.category == "CONSENT_OR_LEGAL":
                consent_count += 1
            elif m.category in ("UNSUPPORTED", "UNSUPPORTED_FIELD"):
                unsupported_count += 1

        return FormMappingResponse(
            mappings=mappings,
            totalFields=len(fields),
            matchedFields=matched,
            unmatchedFields=len(fields) - matched,
            directMappedCount=direct_count,
            aiGeneratedCount=ai_count,
            userInputRequiredCount=user_input_count,
            userConfirmationRequiredCount=user_input_count,
            fileUploadCount=file_count,
            consentLegalCount=consent_count,
            unsupportedCount=unsupported_count
        )

    @classmethod
    def _generate_proposed_answer_for_missing_field(cls, mapping: FormFieldMapping, profile: dict) -> Tuple[Optional[str], str]:
        """Generate a proposed answer for unmapped or missing profile fields without fabricating facts."""
        text = f"{mapping.fieldName or ''} {mapping.questionCategory or ''} {mapping.elementIdentifier}".lower()
        options = mapping.options or []

        # 1. Salary / Compensation
        if any(k in text for k in ["salary", "compensation", "expected ctc", "expected pay", "hourly rate"]):
            ans = "Negotiable based on role responsibilities and industry benchmarks"
            if options:
                matched = match_select_option("negotiable", options) or options[-1]
                return matched, "Salary expectation is a personal preference; proposed 'Negotiable' requires confirmation."
            return ans, "Salary expectation is not specified in profile; proposed standard negotiable response."

        # 2. Security Clearance
        if any(k in text for k in ["clearance", "security clearance", "top secret"]):
            if options:
                no_opt = match_select_option("no", options) or "No"
                return no_opt, "Profile does not indicate active security clearance; proposed 'No' requires confirmation."
            return "No, I do not currently hold a security clearance.", "Profile does not indicate active security clearance."

        # 3. Driver's License
        if any(k in text for k in ["driver's license", "driving license", "valid license"]):
            if options:
                yes_opt = match_select_option("yes", options) or "Yes"
                return yes_opt, "Please confirm if you hold a valid driver's license."
            return "Yes, I hold a valid driver's license.", "Please confirm if you hold a valid driver's license."

        # 4. Notice Period / Joining timeline
        if any(k in text for k in ["notice period", "how soon", "when can you start"]):
            career = profile.get("careerPreferences", {})
            avail = career.get("availability")
            if avail:
                if options:
                    matched = match_select_option(avail, options)
                    if matched:
                        return matched, f"Proposed based on profile availability '{avail}'."
                return str(avail), f"Proposed based on profile availability '{avail}'."
            if options:
                opt_imm = match_select_option("immediate", options) or match_select_option("15 days", options)
                return opt_imm or options[0], "Notice period not specified in profile; please confirm your availability."
            return "Immediate / Standard 2 weeks", "Notice period not specified in profile; please confirm your availability."

        # 5. Unpaid Internship / Compensation preference
        if "unpaid" in text:
            return None, "Personal preference regarding unpaid work is not confirmed in profile; explicit confirmation required."

        # 6. Voluntary demographics / Equal opportunity
        if any(k in text for k in ["veteran", "disability", "race", "ethnicity", "hispanic", "latino", "gender identity"]):
            if options:
                decline = match_select_option("prefer not to say", options) or match_select_option("decline to state", options) or match_select_option("i do not wish to answer", options)
                if decline:
                    return decline, "Voluntary demographic question; proposed 'Prefer not to say' requires your confirmation."
            return "Prefer not to say", "Voluntary demographic question; proposed 'Prefer not to say' requires your confirmation."

        # 7. Yes/No dropdown or radio
        if options and any(o.strip().lower() in ("yes", "no") for o in options):
            no_opt = match_select_option("no", options) or "No"
            return no_opt, "Unspecified yes/no preference in profile; proposed 'No' requires your explicit confirmation."

        # 8. Dropdown options fallback
        if options and len(options) > 1:
            first_meaningful = [o for o in options if "select" not in o.lower() and "choose" not in o.lower()]
            if first_meaningful:
                return first_meaningful[0], f"First available option '{first_meaningful[0]}' proposed for your review."

        # 9. General unmapped text / custom question
        return "None / Not applicable (Please confirm)", f"No specific entry found in profile for '{mapping.fieldName}'; proposed 'None / Not applicable' for confirmation."

    @classmethod
    def map_entire_form(cls, fields: List[FormFieldDescriptor], profile: dict) -> FormMappingResponse:
        """Synchronous form mapping for offline or unit-testing pipelines."""
        mappings: List[FormFieldMapping] = []
        direct_count = 0
        ai_count = 0
        user_input_count = 0
        file_count = 0
        consent_count = 0
        unsupported_count = 0
        matched = 0

        for idx, f in enumerate(fields):
            mapping = cls.classify_and_map_field(f, profile)
            if mapping.category == "AI_GENERATED_ANSWER":
                qid = f.elementId or f.name or f"field_{idx}"
                q_text = f.label or f.placeholder or f.name or "Application question"
                q_cat = classify_question_category(q_text, f.type)
                fb = _generate_deterministic_answer(
                    question_id=qid,
                    question_text=q_text,
                    category=q_cat,
                    profile=profile,
                    company_name="",
                    job_title="",
                    job_description=""
                )
                if fb.status == "generated" and fb.answer:
                    mapping.fillValue = fb.answer
                    mapping.confidence = fb.confidence
                    mapping.reason = fb.reason
                    mapping.questionCategory = fb.category
                    mapping.status = "generated"
                    mapping.requiresReview = False
                elif fb.status == "needs_user_input":
                    mapping.fillValue = None
                    mapping.confidence = 0.0
                    mapping.reason = fb.reason
                    mapping.questionCategory = fb.category
                    mapping.status = "needs_user_input"
                    mapping.category = "USER_INPUT_REQUIRED"
                    mapping.requiresReview = True

            mapping.field_id = mapping.elementIdentifier
            mapping.question = mapping.fieldName or mapping.elementIdentifier
            mapping.questionId = mapping.elementIdentifier
            mapping.filled = False

            if mapping.category in ("USER_INPUT_REQUIRED", "USER_CONFIRMATION_REQUIRED", "UNSUPPORTED", "UNSUPPORTED_FIELD"):
                mapping.requiresReview = True
                mapping.requires_confirmation = True
                mapping.status = mapping.status or "needs_user_input"
                if not mapping.fillValue:
                    prop_ans, conf_reason = cls._generate_proposed_answer_for_missing_field(mapping, profile)
                    mapping.proposed_answer = prop_ans
                    mapping.confirmation_reason = conf_reason or mapping.reason or "Information not found in applicant profile."
                else:
                    mapping.proposed_answer = mapping.fillValue
                    mapping.confirmation_reason = mapping.reason
            elif mapping.category == "CONSENT_OR_LEGAL":
                mapping.requiresReview = True
                mapping.requires_confirmation = True
                mapping.proposed_answer = "[Manual review & confirmation required for legal declaration]"
                mapping.confirmation_reason = "Legal declarations, privacy consents, and accuracy certifications must be manually accepted by the applicant."
            elif mapping.category == "FILE_UPLOAD":
                mapping.requiresReview = True
                mapping.requires_confirmation = True
                mapping.proposed_answer = "[Select resume file from profile]"
                mapping.confirmation_reason = "Browser security restrictions require manual resume document selection."
            else:
                mapping.proposed_answer = mapping.fillValue
                mapping.requires_confirmation = mapping.requiresReview
                mapping.confirmation_reason = mapping.reason if mapping.requiresReview else None

            if mapping.category == "DIRECT_PROFILE_FIELD":
                direct_count += 1
                if mapping.fillValue is not None and mapping.fillValue != "":
                    matched += 1
            elif mapping.category == "AI_GENERATED_ANSWER":
                ai_count += 1
                if mapping.fillValue is not None and mapping.fillValue != "":
                    matched += 1
            elif mapping.category in ("USER_INPUT_REQUIRED", "USER_CONFIRMATION_REQUIRED"):
                user_input_count += 1
            elif mapping.category == "FILE_UPLOAD":
                file_count += 1
            elif mapping.category == "CONSENT_OR_LEGAL":
                consent_count += 1
            elif mapping.category in ("UNSUPPORTED", "UNSUPPORTED_FIELD"):
                unsupported_count += 1

            mappings.append(mapping)

        return FormMappingResponse(
            mappings=mappings,
            totalFields=len(fields),
            matchedFields=matched,
            unmatchedFields=len(fields) - matched,
            directMappedCount=direct_count,
            aiGeneratedCount=ai_count,
            userInputRequiredCount=user_input_count,
            userConfirmationRequiredCount=user_input_count,
            fileUploadCount=file_count,
            consentLegalCount=consent_count,
            unsupportedCount=unsupported_count
        )
