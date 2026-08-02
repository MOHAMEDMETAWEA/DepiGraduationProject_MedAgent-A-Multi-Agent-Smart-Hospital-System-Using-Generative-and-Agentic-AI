import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    role: str = Field(default="patient", pattern="^(patient|doctor)$")
    locale: str = Field(default="ar", pattern="^(en|ar)$")

    # Doctor extras
    license_number: str | None = None
    specialty: str | None = None

    @model_validator(mode="after")
    def validate_doctor_fields(self):
        if self.role == "doctor":
            if not self.license_number:
                raise ValueError("license_number is required for doctor registration")
            if not self.specialty:
                raise ValueError("specialty is required for doctor registration")
        return self


class RegisterResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    role: str
    requires_email_verification: bool = True


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    verified: bool = True


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    sent: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
