from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Prescription Schema
class PrescriptionCreate(BaseModel):
    patient_id: int
    medication_name: str
    dosage: str
    instructions: str

class PrescriptionUpdate(BaseModel):
    status: Optional[str] = None
    price: Optional[float] = None

class PrescriptionOut(BaseModel):
    id: int
    doctor: str
    patient: str
    medication_name: str
    dosage: str
    instructions: str
    status: str
    prescribed_at: datetime
    updated_at: datetime
    price: Optional[float] = None

    class Config:
        from_attributes = True


# Drug Schemas
class DrugCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int

class DrugUpdate(BaseModel):
    description: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None

class DrugOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock_quantity: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
