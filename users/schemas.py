from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import date
from ninja import Router, File, Form
from ninja.files import UploadedFile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    middle_name: Optional[str] = None
    role: str
    address: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    profile_picture: Optional[str] = None

    @field_validator('profile_picture', mode='before')
    @classmethod
    def handle_image_field(cls, value):
        print(value)
        if value and hasattr(value, 'url'):
            return value.url
        return None
    
    class Config: 
        from_attributes = True


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
    ssn: str

class CreateemployeeSchema(BaseModel):
    first_name: str 
    middle_name: str 
    last_name: str 
    phone_number: str 
    gender: str 
    date_of_birth: str 
    address: str 
    ssn: str 
    email: str 
    username: str 
    password: str 
    role: str 
    department: str 
    level: str 

# Login schema
class LoginSchema(BaseModel):
    username: str
    password: str

# Doctor Profile Schemas
class DoctorProfileOut(BaseModel):
    user: UserOut
    department: str
    level: str

    class Config:
        from_attributes = True

class DoctorProfileUpdate(BaseModel):
    department: str
    level: str

# Patient Profile Schemas
class PatientProfileOut(BaseModel):
    user: UserOut
    region: str
    town: str
    kebele: str
    house_number: str
    room_number: Optional[str] = None

    class Config:
        from_attributes = True


class PatientProfileUpdate(BaseModel):
    region: str
    town: str
    kebele: str
    house_number: str

class TokenSchema(BaseModel):
    refresh_token: str

class ApprovePayload(BaseModel):
    user_id: int