from pydantic import BaseModel
from typing import Optional
from datetime import date, time

class AppointmentCreate(BaseModel):
    doctor_id: int
    date: date
    time: time
    reason: Optional[str]

class AppointmentUpdate(BaseModel):
    date: date 
    time: time
    status: Optional[str] = None
    reason: Optional[str] = None

class AppointmentOut(BaseModel):
    id: int
    patient: str
    doctor: str
    date: date
    time: time
    status: str
    reason: Optional[str]
    patient_profile_picture: Optional[str] = None 

    class Config:
        from_attributes = True

class SimplePatientResponse(BaseModel):
    id: int
    patient: str
    doctor: Optional[str] = None