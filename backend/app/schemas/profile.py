from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class PersonalInformation(BaseModel):
    firstName: str = ""
    lastName: str = ""
    fullName: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    address: str = ""
    dateOfBirth: str = ""
    gender: Optional[str] = None
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class EducationItem(BaseModel):
    id: Optional[str] = None
    institution: str = ""
    college: str = ""  # alias for backwards compatibility
    degree: str = ""
    specialization: str = ""
    branch: str = ""  # alias for backwards compatibility
    department: Optional[str] = ""
    startYear: Optional[str] = ""
    graduationYear: str = ""
    currentAcademicYear: Optional[str] = ""
    currentYear: Optional[str] = None  # alias
    cgpa: str = ""
    gradingSystem: Optional[str] = "10-point scale"
    tenthPercentage: Optional[str] = ""
    twelfthPercentage: Optional[str] = ""
    backlogs: Optional[str] = "0"


class Skills(BaseModel):
    programmingLanguages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    cloudPlatforms: List[str] = Field(default_factory=list)  # alias
    devops: List[str] = Field(default_factory=list)
    aiMl: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    softSkills: List[str] = Field(default_factory=list)
    technicalSkills: List[str] = Field(default_factory=list)  # alias


class ExperienceItem(BaseModel):
    id: Optional[str] = None
    company: str = ""
    role: str = ""
    title: str = ""  # alias
    employmentType: Optional[str] = "Full-time"
    startDate: str = ""
    endDate: Optional[str] = ""
    currentlyWorking: bool = False
    duration: str = ""
    responsibilities: Optional[str] = ""
    achievements: Optional[str] = ""
    technologies: List[str] = Field(default_factory=list)
    description: str = ""


class ProjectItem(BaseModel):
    id: Optional[str] = None
    projectName: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    githubUrl: Optional[str] = ""
    liveUrl: Optional[str] = ""
    projectUrl: Optional[str] = None  # alias
    role: Optional[str] = ""
    startDate: Optional[str] = ""
    endDate: Optional[str] = ""


class ProfessionalLinks(BaseModel):
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class CareerPreferences(BaseModel):
    preferredRoles: List[str] = Field(default_factory=list)
    preferredIndustries: List[str] = Field(default_factory=list)
    employmentTypes: List[str] = Field(default_factory=list)  # Internship, Full-time, Part-time
    workModes: List[str] = Field(default_factory=list)  # Remote, Hybrid, On-site
    preferredLocations: List[str] = Field(default_factory=list)
    willingToRelocate: bool = True
    availability: str = "Immediate"
    careerObjective: str = ""
    careerObjectives: str = ""  # alias
    professionalSummary: str = ""
    expectedSalary: Optional[str] = ""
    workAuthorization: Optional[str] = "Authorized to work"
    sponsorshipRequired: Optional[bool] = False


class ProfileBase(BaseModel):
    personalInformation: PersonalInformation = Field(default_factory=PersonalInformation)
    education: List[EducationItem] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    experiences: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    professionalLinks: ProfessionalLinks = Field(default_factory=ProfessionalLinks)
    careerPreferences: CareerPreferences = Field(default_factory=CareerPreferences)
    onboardingCompleted: bool = False


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfilePatch(BaseModel):
    personalInformation: Optional[PersonalInformation] = None
    education: Optional[List[EducationItem]] = None
    skills: Optional[Skills] = None
    experiences: Optional[List[ExperienceItem]] = None
    projects: Optional[List[ProjectItem]] = None
    professionalLinks: Optional[ProfessionalLinks] = None
    careerPreferences: Optional[CareerPreferences] = None
    onboardingCompleted: Optional[bool] = None


class ProfileResponse(ProfileBase):
    id: Optional[str] = Field(default=None, alias="_id")
    userId: str
    completionPercentage: int = 0
    updatedAt: datetime
    createdAt: Optional[datetime] = None

    class Config:
        populate_by_name = True


class ProfileCompletionResponse(BaseModel):
    completionPercentage: int
    missingRequired: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    hasProfile: bool = False


def calculate_profile_completion(profile_data: dict) -> tuple[int, List[str], List[str]]:
    """
    Calculate profile completion percentage, missing required fields, and suggested next steps.
    Score breakdown:
    - Personal Information: 25%
    - Education: 20%
    - Skills: 20%
    - Projects / Experience: 15%
    - Career Preferences: 10%
    - Resume: 10%
    Total: 100%
    """
    score = 0
    missing = []
    suggestions = []

    personal = profile_data.get("personalInformation") or profile_data.get("personal", {})
    # First & Last name: 10%
    first = personal.get("firstName") or personal.get("fullName", "")
    last = personal.get("lastName", "")
    if first and (last or personal.get("fullName")):
        score += 10
    else:
        missing.append("Full Name")

    # Email: 5%
    if personal.get("email"):
        score += 5
    else:
        missing.append("Email Address")

    # Phone: 5%
    if personal.get("phone"):
        score += 5
    else:
        missing.append("Phone Number")

    # Location (City/Country): 5%
    if personal.get("city") or personal.get("country"):
        score += 5
    else:
        suggestions.append("Add your current city and country")

    # Education: 20%
    education = profile_data.get("education", [])
    if education and len(education) > 0 and (education[0].get("institution") or education[0].get("college")):
        first_edu = education[0]
        score += 10
        if first_edu.get("degree"):
            score += 5
        if first_edu.get("graduationYear"):
            score += 5
        if not first_edu.get("cgpa"):
            suggestions.append("Add your CGPA or academic percentage")
    else:
        missing.append("Education details (Degree & College)")

    # Skills: 20%
    skills = profile_data.get("skills", {})
    all_skills = []
    for k in ["programmingLanguages", "frameworks", "databases", "cloud", "cloudPlatforms", "tools", "technicalSkills", "devops", "aiMl"]:
        items = skills.get(k, [])
        if isinstance(items, list):
            all_skills.extend(items)
    
    unique_skills = set(filter(None, all_skills))
    if len(unique_skills) >= 1:
        score += 10
    if len(unique_skills) >= 3:
        score += 5
    if len(unique_skills) >= 6:
        score += 5
    
    if len(unique_skills) < 3:
        suggestions.append("Add at least 3-5 technical skills to improve autofill quality")

    # Projects / Experience: 15%
    projects = profile_data.get("projects", [])
    experiences = profile_data.get("experiences", [])
    
    has_proj = projects and len(projects) > 0 and projects[0].get("projectName")
    has_exp = experiences and len(experiences) > 0 and experiences[0].get("company")
    
    if has_proj:
        score += 10
    if has_exp:
        score += 5
    elif has_proj and len(projects) > 1:
        score += 5  # Freshers with 2+ projects get full score
    
    if not has_proj and not has_exp:
        suggestions.append("Add at least one technical project or internship")

    # Career Preferences: 10%
    career = profile_data.get("careerPreferences", {})
    roles = career.get("preferredRoles", [])
    if roles and len(roles) > 0:
        score += 5
    else:
        suggestions.append("Specify your target job roles (e.g. Frontend Developer)")

    summary = career.get("professionalSummary") or career.get("careerObjective") or career.get("careerObjectives")
    if summary and len(summary.strip()) > 10:
        score += 5
    else:
        suggestions.append("Add a 2-3 sentence professional summary")

    # Links: Bonus up to max 100%
    links = profile_data.get("professionalLinks", {})
    if links.get("linkedin") or personal.get("linkedin"):
        score += 5
    if links.get("github") or personal.get("github"):
        score += 5

    final_score = min(100, max(0, score))
    return final_score, missing, suggestions
