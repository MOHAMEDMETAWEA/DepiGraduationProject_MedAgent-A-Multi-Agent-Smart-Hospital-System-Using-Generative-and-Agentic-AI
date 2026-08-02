"""Doctor schemas — request/response validation."""

from pydantic import BaseModel


class DoctorProfileResponse(BaseModel):
    id: str
    user_id: str
    license_number: str
    specialty: str
    bio: str | None = None
    years_of_experience: int | None = None
    languages: list[str] = ["ar"]
    approval_status: str
    created_at: str


class DoctorPublicResponse(BaseModel):
    """Public doctor info (for patient search/browsing)."""

    id: str
    user_id: str
    full_name: str
    specialty: str
    years_of_experience: int | None = None
    languages: list[str] = ["ar"]
