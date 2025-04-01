from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# Shared User Schema
class UserOut(BaseModel):
    id: int
    phone_number: str
    email: EmailStr
    username: str
    role: str
    address: str

    class Config:
        from_attributes = True

# Signup Schema
class SignupSchema(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    phone_number: str
    gender: str
    date_of_birth: str
    address: str
    region: str
    town: str
    kebele: str
    house_number: str
    profile_picture: Optional[str] = None

class CreateemployeeSchema(UserOut):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., pattern="^(doctor|pharmacist|lab_technician|cashier|record_officer)$")

# Login schema
class LoginSchema(BaseModel):
    username: str
    password: str

# Manager Profile Schemas
class ManagerProfileOut(UserOut):
    ssn: str

    class Config:
        from_attributes = True


class ManagerProfileUpdate(BaseModel):
    ssn: str

# Doctor Profile Schemas
class DoctorProfileOut(UserOut):
    ssn: str
    department: str
    level: str

    class Config:
        from_attributes = True

class DoctorProfileUpdate(BaseModel):
    ssn: str
    department: str
    level: str

# Patient Profile Schemas
class PatientProfileOut(UserOut):
    region: str
    town: str
    kebele: str
    house_number: str
    room_number: str

    class Config:
        from_attributes = True

class PatientProfileUpdate(BaseModel):
    region: str
    town: str
    kebele: str
    house_number: str

# Pharmacist Profile Schemas
class PharmacistProfileOut(UserOut):
    ssn: str

    class Config:
        from_attributes = True

class PharmacistProfileUpdate(BaseModel):
    ssn: str

# Lab Technician Profile Schemas
class LabTechnicianProfileOut(UserOut):
    ssn: str

    class Config:
        from_attributes = True

class LabTechnicianProfileUpdate(BaseModel):
    ssn: str

# Cashier Profile Schemas
class CashierProfileOut(UserOut):
    ssn: str

    class Config:
        from_attributes = True

class CashierProfileUpdate(BaseModel):
    ssn: str

# Record Officer Profile Schemas
class RecordOfficerProfileOut(UserOut):
    ssn: str

    class Config:
        from_attributes = True

class RecordOfficerProfileUpdate(BaseModel):
    ssn: str
