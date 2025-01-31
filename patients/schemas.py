from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from users.schemas import PatientProfileOut  

# Appointment Schema
class AppointmentOut(BaseModel):
    id: int
    doctor: str
    date: datetime
    time: str
    reason: str
    status: str

    class Config:
        from_attributes = True  

# Lab Test Schema
class LabTestOut(BaseModel):
    id: int
    test_name: str
    status: str
    result: Optional[str]

    class Config:
        from_attributes = True  

# Prescription Schema
class PrescriptionOut(BaseModel):
    id: int
    doctor: str
    medication_name: str
    dosage: str
    instructions: str
    status: str

    class Config:
        from_attributes = True 

# Invoice Schema
class InvoiceOut(BaseModel):
    id: int
    amount: float
    description: str
    status: str

    class Config:
        from_attributes = True  

#  Medical History Response Schema
class MedicalHistoryOut(BaseModel):
    appointments: List[AppointmentOut]
    lab_tests: List[LabTestOut]
    prescriptions: List[PrescriptionOut]

# Billing History Response Schema
class BillingHistoryOut(BaseModel):
    invoices: List[InvoiceOut]

# Patient Comment Schema
class PatientCommentCreate(BaseModel):
    message: str = Field(..., min_length=5, max_length=500)



