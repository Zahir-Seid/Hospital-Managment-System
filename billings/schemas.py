from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InvoiceCreate(BaseModel):
    patient_id: int
    amount: float
    description: str

class InvoiceUpdate(BaseModel):
    status: Optional[str] = None

class InvoiceOut(BaseModel):
    id: int
    patient: str
    amount: float
    description: str
    status: str
    chapa_payment_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
