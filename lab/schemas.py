from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LabTestCreate(BaseModel):
    patient_id: int
    test_name: str

class LabTestUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None

class LabTestOut(BaseModel):
    id: int
    doctor: str
    patient: str
    test_name: str
    status: str
    result: Optional[str] = None
    ordered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    sender: str
    receiver: str
    subject: str
    message: str
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True