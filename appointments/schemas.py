from pydantic import BaseModel
from typing import Optional
from datetime import date, time

class AppointmentCreate(BaseModel):
    doctor_id: int
    date: date
    time: time
    reason: Optional[str]

class AppointmentUpdate(BaseModel):
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

    class Config:
        orm_mode = True
