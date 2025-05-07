from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime
from users.models import User

class InvoiceCreate(BaseModel):
    patient_id: int
    amount: float
    description: str

class InvoiceUpdate(BaseModel):
    amount: float

    class Config:
        from_attributes = True

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


