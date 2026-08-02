import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None = None
    role: str
    is_email_verified: bool
    locale: str
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PatientProfileResponse(BaseModel):
    date_of_birth: date | None = None
    gender: str | None = None
    blood_type: str | None = None
    allergies: list = []
    chronic_conditions: list = []
    current_medications: list = []
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class DoctorProfileResponse(BaseModel):
    license_number: str
    specialty: str
    bio: str | None = None
    years_of_experience: int | None = None
    languages: list = []
    approval_status: str


class MeResponse(BaseModel):
    user: UserResponse
    profile: PatientProfileResponse | DoctorProfileResponse | None = None


class UpdateMeRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = None
    locale: str | None = Field(None, pattern="^(ar|en)$")


class UpdatePatientProfileRequest(BaseModel):
    date_of_birth: date | None = None
    gender: str | None = None
    blood_type: str | None = None
    allergies: list | None = None
    chronic_conditions: list | None = None
    current_medications: list | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class UpdateDoctorProfileRequest(BaseModel):
    specialty: str | None = None
    bio: str | None = None
    years_of_experience: int | None = None
    languages: list | None = None
