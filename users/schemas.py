# update ssn is experimental should be removed in the end

from pydantic import BaseModel, EmailStr, Field
# Shared User Schema
class UserOut(BaseModel):
    id: int
    phone_number: str
    email: EmailStr
    role: str
    address: str

    class Config:
        from_attributes = True

# Signup Schema
class SignupSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., pattern="^(doctor|patient|pharmacist|lab_technician|cashier|record_officer)$")

# Login schema
class LoginSchema(BaseModel):
    email: EmailStr
    password: str

# Manager Profile Schemas
class ManagerProfileOut(BaseModel):
    ssn: str

    class Config:
        from_attributes = True


class ManagerProfileUpdate(BaseModel):
    ssn: str


# Doctor Profile Schemas
class DoctorProfileOut(BaseModel):
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
class PatientProfileOut(BaseModel):
    region: str
    town: str
    kebele: str
    house_number: str

    class Config:
        from_attributes = True


class PatientProfileUpdate(BaseModel):
    region: str
    town: str
    kebele: str
    house_number: str


# Pharmacist Profile Schemas
class PharmacistProfileOut(BaseModel):
    ssn: str

    class Config:
        from_attributes = True


class PharmacistProfileUpdate(BaseModel):
    ssn: str


# Lab Technician Profile Schemas
class LabTechnicianProfileOut(BaseModel):
    ssn: str

    class Config:
        from_attributes = True


class LabTechnicianProfileUpdate(BaseModel):
    ssn: str


# Cashier Profile Schemas
class CashierProfileOut(BaseModel):
    ssn: str

    class Config:
        from_attributes = True


class CashierProfileUpdate(BaseModel):
    ssn: str
