import asyncio
import uuid
from datetime import date

from app.core.database import get_session
from app.core.security import hash_password
from app.models.doctor_profile import DoctorProfile
from app.models.patient_profile import PatientProfile
from app.models.users import User
from sqlalchemy import select


async def seed():
    async with get_session() as session:
        # Check if users already exist
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Users already exist, skipping seeding.")
            return

        # 1. Admin User
        admin = User(
            id=uuid.uuid4(),
            email="admin@medagent.com",
            hashed_password=hash_password("Admin123"),
            full_name="Hossam Admin",
            role="admin",
            is_email_verified=True,
            locale="ar",
        )
        session.add(admin)
        await session.flush()

        # 2. Sample Patients

        patient_user = User(
            id=uuid.uuid4(),
            email="patient@medagent.com",
            hashed_password=hash_password("Patient123"),
            full_name="Sara Patient",
            role="patient",
            is_email_verified=True,
            locale="ar",
        )
        session.add(patient_user)
        await session.flush()

        patient_profile = PatientProfile(
            user_id=patient_user.id,
            date_of_birth=date(1991, 5, 20),
            gender="female",
            allergies=["penicillin"],
            chronic_conditions=["asthma"],
            current_medications=[{"name": "Ventolin", "dose": "2 puffs PRN"}],
            emergency_contact_name="Ahmed Mahmoud",
            emergency_contact_phone="+201234567890",
        )
        session.add(patient_profile)

        # 3. Sample Doctors (pre approved for dev)
        doctor_user = User(
            id=uuid.uuid4(),
            email="doctor@medagent.com",
            hashed_password=hash_password("Doctor123"),
            full_name="Dr. Ahmed Hassan",
            role="doctor",
            is_email_verified=True,
            locale="ar",
        )
        session.add(doctor_user)
        await session.flush()

        doctor_profile = DoctorProfile(
            user_id=doctor_user.id,
            license_number="EG-12345-DOC",
            specialty="General Practice",
            bio="Experienced GP with 15 years of practice.",
            years_of_experience=15,
            languages=["ar", "en"],
            approval_status="approved",
        )
        session.add(doctor_profile)

        await session.commit()
        print("Seed complete: 1 admin, 1 patient, 1 doctor created.")


if __name__ == "__main__":
    asyncio.run(seed())
